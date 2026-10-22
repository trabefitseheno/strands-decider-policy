import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from patterns.notice_relevance import DeciderClient, NOTICE_LEVEL

SEEN = {}


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        SEEN["path"] = self.path
        SEEN["body"] = json.loads(self.rfile.read(int(self.headers["content-length"])))
        out = {"model": "m", "usage": {}, "answers": {"reading_level": {
            "type": "choice", "choice": "plain", "probabilities": {"plain": 0.9, "standard": 0.05, "detailed": 0.05}, "confidence": 0.85}}}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def test_client_wire_shape_and_latency():
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        c = DeciderClient(f"http://127.0.0.1:{srv.server_port}")
        ans = c.ask("state", {"reading_level": NOTICE_LEVEL.to_question()})
    finally:
        srv.shutdown()
    assert SEEN["path"] == "/v1/systemone"
    q = SEEN["body"]["questions"]["reading_level"]
    assert q["type"] == "choice" and set(q["criteria"]) == {"plain", "standard", "detailed"}
    assert ans["reading_level"]["choice"] == "plain" and c.last_latency_ms is not None
