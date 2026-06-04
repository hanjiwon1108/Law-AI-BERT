import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from predict_bert import BertRiskPredictor


class Handler(BaseHTTPRequestHandler):
    predictor: BertRiskPredictor

    def _send_json(self, status: int, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json(200, {"ok": True})

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"ok": True, "model": "contract-risk-bert"})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/analyze":
            self._send_json(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            text = payload.get("text", "")
            contract_type = payload.get("contractType", "general")
            if not text.strip():
                self._send_json(400, {"error": "text is required"})
                return
            self._send_json(200, self.predictor.analyze(text, contract_type))
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the fine-tuned BERT contract risk model.")
    parser.add_argument("--model-dir", default="models/contract-risk-bert")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print(
        f"[startup] loading model from {args.model_dir} (host={args.host}, port={args.port})",
        flush=True,
    )
    start = time.perf_counter()
    Handler.predictor = BertRiskPredictor(args.model_dir)
    elapsed = time.perf_counter() - start
    print(f"[startup] model loaded in {elapsed:.2f}s", flush=True)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[startup] server bound on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
