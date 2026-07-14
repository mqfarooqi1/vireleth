"""
Zero-dependency web server for the AI chatbot.

Run it with:   python server.py
Then open:     http://127.0.0.1:8000

Uses only the Python standard library — nothing to pip install.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
import providers

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "NexusAI/1.0"

    # -- helpers -----------------------------------------------------------
    def _send(self, status, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status, obj):
        self._send(status, json.dumps(obj))

    def log_message(self, fmt, *args):  # quieter, tidy logging
        print("  %s - %s" % (self.address_string(), fmt % args))

    # -- GET ---------------------------------------------------------------
    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path == "/" or path == "/index.html":
            return self._serve_index()

        if path == "/api/config":
            return self._send_json(200, config.client_config())

        if path == "/manifest.webmanifest":
            return self._serve_manifest()

        # Static files from ./static (never allow escaping the directory)
        rel = path.lstrip("/")
        full = os.path.normpath(os.path.join(config.STATIC_DIR, rel))
        if full.startswith(config.STATIC_DIR) and os.path.isfile(full):
            ext = os.path.splitext(full)[1].lower()
            ctype = _CONTENT_TYPES.get(ext, "application/octet-stream")
            with open(full, "rb") as fh:
                return self._send(200, fh.read(), ctype)

        return self._send(404, "Not found", "text/plain; charset=utf-8")

    def _serve_index(self):
        index_path = os.path.join(config.STATIC_DIR, "index.html")
        with open(index_path, "r", encoding="utf-8") as fh:
            html = fh.read()
        # Inject config so the page has no extra round-trip / no flash.
        cfg_json = json.dumps(config.client_config())
        html = html.replace("__APP_CONFIG__", cfg_json)
        return self._send(200, html, "text/html; charset=utf-8")

    def _serve_manifest(self):
        manifest = {
            "name": config.BRAND,
            "short_name": config.BRAND,
            "description": config.TAGLINE,
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#0d1117",
            "theme_color": "#0d1117",
            "icons": [
                {"src": "/icon.svg", "sizes": "192x192", "type": "image/svg+xml", "purpose": "any"},
                {"src": "/icon.svg", "sizes": "512x512", "type": "image/svg+xml", "purpose": "any"},
                {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "maskable"},
            ],
        }
        return self._send(
            200, json.dumps(manifest), "application/manifest+json; charset=utf-8"
        )

    # -- POST --------------------------------------------------------------
    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path != "/api/chat":
            return self._send(404, "Not found", "text/plain; charset=utf-8")

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return self._send_json(400, {"error": "Invalid JSON body"})

        messages = data.get("messages", [])
        mode = data.get("mode", "general")
        if mode not in config.SYSTEM_PROMPTS:
            mode = "general"
        if not isinstance(messages, list) or not messages:
            return self._send_json(400, {"error": "No messages provided"})

        # Keep only the fields we need, cap history length for safety.
        clean = [
            {"role": m.get("role", "user"), "content": str(m.get("content", ""))}
            for m in messages
            if m.get("content")
        ][-40:]

        try:
            result = providers.chat(clean, mode)
        except Exception as exc:  # never crash the request
            return self._send_json(200, {"reply": f"⚠️ Server error: {exc}", "tools_used": []})

        return self._send_json(200, result)


def main():
    httpd = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    url = f"http://{config.HOST}:{config.PORT}"
    mode = "DEMO (no API key)" if config.DEMO_MODE else f"LIVE ({config.MODEL})"
    print("=" * 60)
    print(f"  {config.BRAND} is running in {mode} mode")
    print(f"  Open your browser at:  {url}")
    print("  Press Ctrl+C to stop.")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down. Bye!")
        httpd.server_close()


if __name__ == "__main__":
    main()
