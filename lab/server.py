from __future__ import annotations
import argparse, concurrent.futures, importlib, json, mimetypes, os, sqlite3, threading, time, traceback, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote
from .core import ROOT, RUNTIME, clean
CATALOG = json.loads((ROOT / 'catalog.json').read_text())
META = {x['id']: x for x in CATALOG}
ENGINES = {}
LOCKS = {}
CACHE_LOCK = threading.Lock()
JOBS = {}
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2)

def db():
    RUNTIME.mkdir(exist_ok=True)
    c = sqlite3.connect(RUNTIME / 'lab.sqlite', timeout=30)
    c.execute('CREATE TABLE IF NOT EXISTS states(project TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, project TEXT, action TEXT, timestamp REAL, seconds REAL, status TEXT, result TEXT)')
    return c

def get_engine(project):
    if project not in META:
        raise KeyError('Unknown project')
    with CACHE_LOCK:
        if project not in ENGINES:
            engine = importlib.import_module('lab.' + META[project]['module']).Engine()
            with db() as c:
                row = c.execute('SELECT payload FROM states WHERE project=?', (project,)).fetchone()
            if row:
                try:
                    engine.restore(json.loads(row[0]))
                except (ValueError, KeyError, TypeError):
                    pass
            ENGINES[project] = engine
            LOCKS[project] = threading.RLock()
    return ENGINES[project]

def persist(project, e):
    payload = e.persist() if hasattr(e, 'persist') else e.snapshot()
    with db() as c:
        c.execute('INSERT OR REPLACE INTO states VALUES (?,?)', (project, json.dumps(clean(payload), allow_nan=False)))

def run_action(project, action, p, job=None):
    e = get_engine(project)
    start = time.monotonic()
    rid = job['id'] if job else uuid.uuid4().hex
    status = 'succeeded'
    result = None
    with LOCKS[project]:
        if not job:
            e.cancel_event.clear()
        try:
            e.check_cancel()
            result = e.dispatch(action, p)
            e.check_cancel()
            persist(project, e)
        except InterruptedError:
            status = 'cancelled'
            raise
        except Exception:
            status = 'failed'
            raise
        finally:
            if action not in ['state', 'step']:
                with db() as c:
                    c.execute('INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?)', (rid, project, action, time.time(), time.monotonic() - start, status, json.dumps(clean(result), allow_nan=False)))
    return {'state': e.snapshot(), 'result': clean(result), 'run_id': rid}

def work(job, p):
    job['status'] = 'running'
    try:
        job['response'] = run_action(job['project'], job['action'], p, job)
        job['status'] = 'succeeded'
    except InterruptedError:
        job['status'] = 'cancelled'
        job['error'] = 'Cancelled by user'
    except Exception as exc:
        job['status'] = 'failed'
        job['error'] = str(exc)
        traceback.print_exc()
    job['finished'] = time.time()

class Handler(BaseHTTPRequestHandler):
    server_version = 'IshdeepAILab/2.0'

    def log_message(self, fmt, *args):
        if os.environ.get('LAB_QUIET') != '1':
            super().log_message(fmt, *args)

    def send(self, data, status=200, kind='application/json; charset=utf-8', filename=None):
        raw = json.dumps(clean(data), allow_nan=False).encode() if kind.startswith('application/json') else data.encode() if isinstance(data, str) else data
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'same-origin')
        if filename:
            self.send_header('Content-Disposition', 'attachment; filename="' + filename + '"')
        self.end_headers()
        self.wfile.write(raw)

    def fail(self, e):
        self.send({'error': str(e)}, 400 if isinstance(e, (ValueError, KeyError, IndexError)) else 500)

    def safe_file(self, root, name):
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise KeyError('File not found')
        self.send(path.read_bytes(), kind=mimetypes.guess_type(str(path))[0] or 'application/octet-stream')

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        try:
            if path in ['/health', '/ready']:
                return self.send({'status': 'ready', 'version': '2.0.0', 'projects': len(CATALOG)})
            if path == '/api/catalog':
                return self.send(CATALOG)
            if path.startswith('/api/jobs/'):
                job = JOBS.get(path.split('/')[-1])
                if not job:
                    raise KeyError('Unknown job')
                return self.send({k: v for k, v in job.items() if k != 'future'})
            if path == '/api/runs':
                with db() as c:
                    rows = c.execute('SELECT id,project,action,timestamp,seconds,status,result FROM runs ORDER BY timestamp DESC LIMIT 150').fetchall()
                return self.send([dict(zip(['id', 'project', 'action', 'timestamp', 'seconds', 'status', 'result'], list(r[:-1]) + [json.loads(r[-1])])) for r in rows])
            if path.startswith('/api/export/'):
                pid = path.split('/')[-1]
                e = get_engine(pid)
                with LOCKS[pid]:
                    payload = {'project': META[pid], 'state': e.snapshot(), 'exported_at': time.time(), 'release': '2.0.0'}
                return self.send(json.dumps(clean(payload), indent=2), kind='application/octet-stream', filename=pid + '-report.json')
            if path.startswith('/api/') and path.endswith('/state'):
                pid = path.split('/')[2]
                e = get_engine(pid)
                with LOCKS[pid]:
                    return self.send({'state': e.snapshot()})
            if path.startswith('/media/'):
                return self.safe_file(RUNTIME / 'media', path[len('/media/'):])
            if path.startswith('/assets/'):
                return self.safe_file(ROOT / 'web', path[len('/assets/'):])
            if path == '/' or path.startswith('/p/'):
                return self.safe_file(ROOT / 'web', 'index.html')
            raise KeyError('Route not found')
        except Exception as e:
            self.fail(e)

    def do_POST(self):
        try:
            origin = self.headers.get('Origin')
            host = self.headers.get('Host')
            if origin and urlparse(origin).netloc != host:
                raise ValueError('Cross-origin writes are disabled')
            if 'application/json' not in self.headers.get('Content-Type', ''):
                raise ValueError('Expected application/json')
            size = int(self.headers.get('Content-Length', 0))
            if size <= 0 or size > 6000000:
                raise ValueError('Request must contain 1–6,000,000 bytes')
            p = json.loads(self.rfile.read(size))
            path = urlparse(self.path).path
            if not isinstance(p, dict):
                raise ValueError('Request body must be an object')
            if path.startswith('/api/jobs/') and path.endswith('/cancel'):
                jid = path.split('/')[-2]
                job = JOBS[jid]
                get_engine(job['project']).cancel_event.set()
                return self.send({'cancel_requested': True})
            parts = path.strip('/').split('/')
            if len(parts) != 3 or parts[0] != 'api':
                raise ValueError('Unknown API action route')
            _, pid, action = parts
            e = get_engine(pid)
            if p.pop('_async', False):
                if any((j['project'] == pid and j['status'] in ['queued', 'running'] for j in JOBS.values())):
                    raise ValueError('This project already has a running job')
                e.cancel_event.clear()
                job = {'id': uuid.uuid4().hex, 'project': pid, 'action': action, 'status': 'queued', 'created': time.time()}
                JOBS[job['id']] = job
                job['future'] = POOL.submit(work, job, p)
                return self.send({'job_id': job['id']}, 202)
            return self.send(run_action(pid, action, p))
        except Exception as e:
            self.fail(e)

def main():
    parser = argparse.ArgumentParser(description='Run all 15 Ishdeep AI Lab applications locally')
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', '8765')))
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--strictPort', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--project', choices=list(META))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f'Ishdeep AI Lab → http://{args.host}:{args.port}' + ('/p/' + args.project if args.project else ''), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        POOL.shutdown(wait=False, cancel_futures=True)
if __name__ == '__main__':
    main()
