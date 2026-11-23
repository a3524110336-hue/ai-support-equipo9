"""API HTTP: POST /api/analyze  (solo libreria estandar de Python)."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from engine import generative, traditional
from engine.contract import ValidationError, validate_request

MAX_BODY = 8 * 1024


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok"})
        self._send(404, {"error": "Ruta no encontrada"})

    def do_POST(self):
        if self.path != "/api/analyze":
            return self._send(404, {"error": "Ruta no encontrada"})
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type != "application/json":
            return self._send(415, {"error": "Content-Type debe ser application/json"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._send(400, {"error": "Content-Length invalido"})
        if length > MAX_BODY:
            return self._send(413, {"error": f"El cuerpo excede {MAX_BODY} bytes"})
        if length <= 0:
            return self._send(400, {"error": "Cuerpo vacio"})
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            message, mode = validate_request(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._send(400, {"error": "JSON invalido"})
        except ValidationError as e:
            return self._send(400, {"error": str(e)})
        try:
            engine = generative if mode == "generative" else traditional
            return self._send(200, engine.classify(message))
        except generative.GenerativeError as e:
            # Mensaje generico: no se exponen trazas, URLs internas ni credenciales.
            return self._send(502, {"error": "Fallo del motor generativo", "detail": str(e)})
        except Exception:
            return self._send(500, {"error": "Error interno"})

    def log_message(self, fmt, *args):  # sin volcar cuerpos (pueden traer datos sensibles)
        print(f"{self.address_string()} {fmt % args}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"AI Support Engine en http://127.0.0.1:{port}/api/analyze")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
