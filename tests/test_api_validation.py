"""Pruebas de la validacion de entrada de POST /api/analyze contra el servidor real.

Levantan server.py en un puerto libre dentro del mismo proceso. Solo usan el motor
tradicional, asi que no necesitan Ollama.
"""
import http.client
import json
import pathlib
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import server  # noqa: E402


class ApiValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def post(self, body, content_type="application/json", headers=None, path="/api/analyze"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        h = {"Content-Type": content_type, "Content-Length": str(len(data))}
        h.update(headers or {})
        conn.request("POST", path, body=data, headers=h)
        resp = conn.getresponse()
        payload = json.loads(resp.read().decode("utf-8"))
        conn.close()
        return resp.status, payload

    def test_ok_traditional(self):
        status, out = self.post(json.dumps({"message": "No puedo iniciar sesion"}))
        self.assertEqual(status, 200)
        self.assertEqual(set(out), {"category", "priority", "response", "requiresHumanReview", "mode"})
        self.assertEqual((out["category"], out["mode"]), ("ACCESS", "traditional"))

    def test_content_type_with_charset_is_accepted(self):
        status, _ = self.post(json.dumps({"message": "error 500 al guardar"}),
                              content_type="application/json; charset=utf-8")
        self.assertEqual(status, 200)

    def test_wrong_content_type_is_415(self):
        status, _ = self.post("message=hola", content_type="application/x-www-form-urlencoded")
        self.assertEqual(status, 415)

    def test_body_too_large_is_413(self):
        status, _ = self.post(json.dumps({"message": "a" * 9000}))
        self.assertEqual(status, 413)

    def test_invalid_json_is_400(self):
        status, out = self.post("{no es json")
        self.assertEqual((status, out["error"]), (400, "JSON invalido"))

    def test_invalid_content_length_is_400(self):
        status, _ = self.post("{}", headers={"Content-Length": "abc"})
        self.assertEqual(status, 400)

    def test_contract_violations_are_400(self):
        bodies = ({"message": ""}, {"message": "   "}, {"message": 123},
                  {"message": "hola", "mode": "magia"}, {"message": "hola", "admin": True},
                  {"message": "x" * 2001}, ["no", "es", "objeto"])
        for body in bodies:
            with self.subTest(body=str(body)[:40]):
                status, out = self.post(json.dumps(body))
                self.assertEqual(status, 400)
                self.assertIn("error", out)

    def test_unknown_route_is_404(self):
        status, _ = self.post(json.dumps({"message": "hola"}), path="/api/otra")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
