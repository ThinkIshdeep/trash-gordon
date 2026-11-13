import json, threading, unittest, urllib.request, urllib.error
from lab.server import Handler, ThreadingHTTPServer

class APITests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as r:
            return json.load(r)

    def post(self, path, p, origin=None):
        req = urllib.request.Request(self.base + path, data=json.dumps(p).encode(), headers={'Content-Type': 'application/json', **({'Origin': origin} if origin else {})})
        return urllib.request.urlopen(req)

    def test_catalog(self):
        self.assertEqual(len(self.get('/api/catalog')), 1)

    def test_readiness(self):
        self.assertEqual(self.get('/ready')['status'], 'ready')

    def test_all_project_states(self):
        for project in self.get('/api/catalog'):
            with self.subTest(project=project['id']):
                self.assertIn('state', self.get('/api/' + project['id'] + '/state'))

    def test_invalid_operation_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.post('/api/trash-gordon/run_arbitrary_code', {})
        self.assertEqual(cm.exception.code, 400)

    def test_cross_origin_write_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.post('/api/trash-gordon/advance', {}, 'https://untrusted.example')
        self.assertEqual(cm.exception.code, 400)

    def test_export_valid_json(self):
        self.assertEqual(self.get('/api/export/trash-gordon')['project']['id'], 'trash-gordon')

    def test_static_path_escape_blocked(self):
        with self.assertRaises(urllib.error.HTTPError):
            self.get('/assets/../../catalog.json')

    def test_runs_available(self):
        self.assertIsInstance(self.get('/api/runs'), list)
if __name__ == '__main__':
    unittest.main()
