"""Run actual bundled evaluations and write their full outputs. No fixture metrics."""
import argparse, importlib, json, platform, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.core import clean

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only')
    args = parser.parse_args()
    catalog = json.loads((ROOT / 'catalog.json').read_text())
    report = {'python': platform.python_version(), 'platform': platform.platform(), 'results': []}
    for project in catalog:
        if args.only and project['id'] != args.only:
            continue
        start = time.monotonic()
        try:
            engine = importlib.import_module('lab.' + project['module']).Engine()
            extra = {}
            if project['module'] == 'city':
                extra = engine.train({'episodes': 60})
            if project['module'] == 'murphy':
                extra = engine.search({'budget': 120})
                if engine.state['gallery']:
                    extra['reduction'] = engine.reduce({})
            result = engine.evaluate({'trials': 6})
            if 'checks' in result and (not all(result['checks'].values())):
                raise AssertionError('One or more domain invariant checks failed: ' + str(result['checks']))
            record = {'project': project['id'], 'status': 'passed', 'seconds': time.monotonic() - start, 'evaluation': clean(result), 'additional': clean(extra)}
            print(project['id'], 'PASS', round(record['seconds'], 2), 's', flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            record = {'project': project['id'], 'status': 'failed', 'seconds': time.monotonic() - start, 'error': str(e)}
            print(project['id'], 'FAIL', e, flush=True)
        report['results'].append(record)
    out = ROOT / 'reports' / 'evaluation-results.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(clean(report), indent=2, allow_nan=False))
    print('Saved', out)
    return int(any((x['status'] != 'passed' for x in report['results'])))
if __name__ == '__main__':
    raise SystemExit(main())
