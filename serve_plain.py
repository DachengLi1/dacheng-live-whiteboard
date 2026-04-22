#!/usr/bin/env python3
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
import os

PORT = int(os.environ.get('PORT', '8787'))
ROOT = os.environ.get('WHITEBOARD_ROOT', os.path.dirname(__file__))

class ReuseServer(ThreadingHTTPServer):
    allow_reuse_address = True

Handler = partial(SimpleHTTPRequestHandler, directory=ROOT)
httpd = ReuseServer(('0.0.0.0', PORT), Handler)
print(f'Serving plain whiteboard at http://0.0.0.0:{PORT}/ from {ROOT}', flush=True)
httpd.serve_forever()
