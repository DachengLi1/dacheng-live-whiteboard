#!/usr/bin/env python3
import http.server
import os
import socketserver
import sys
from functools import partial

PORT = int(os.environ.get("PORT", "8787"))
TOKEN = os.environ["WHITEBOARD_TOKEN"]
ROOT = os.environ.get("WHITEBOARD_ROOT", os.path.dirname(__file__))

class SecretWhiteboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def _allowed_path(self):
        return f"/{TOKEN}"

    def do_GET(self):
        allowed = self._allowed_path()
        if self.path == "/":
            self.path = "/index.html"
            return super().do_GET()
        if self.path == allowed:
            self.send_response(302)
            self.send_header("Location", allowed + "/")
            self.end_headers()
            return
        if self.path.startswith(allowed + "/"):
            original = self.path
            self.path = self.path[len(allowed):] or "/"
            try:
                return super().do_GET()
            finally:
                self.path = original
        return super().do_GET()

    def do_HEAD(self):
        allowed = self._allowed_path()
        if self.path == "/":
            self.path = "/index.html"
            return super().do_HEAD()
        if self.path == allowed:
            self.send_response(302)
            self.send_header("Location", allowed + "/")
            self.end_headers()
            return
        if self.path.startswith(allowed + "/"):
            original = self.path
            self.path = self.path[len(allowed):] or "/"
            try:
                return super().do_HEAD()
            finally:
                self.path = original
        return super().do_HEAD()

    def log_message(self, format, *args):
        sys.stdout.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), format % args))
        sys.stdout.flush()

Handler = partial(SecretWhiteboardHandler, directory=ROOT)

with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    print(f"Serving whiteboard at http://0.0.0.0:{PORT}/{TOKEN}/ from {ROOT}", flush=True)
    httpd.serve_forever()
