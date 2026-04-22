#!/usr/bin/env python3
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os

PORT = int(os.environ.get('PORT', '8788'))
ROOT = Path(os.environ.get('WHITEBOARD_ROOT', os.path.dirname(__file__))).resolve()
MONITOR_BASE = os.environ.get('MONITOR_BASE', 'http://127.0.0.1:8890')
STATE_DIR = ROOT / 'state_backups'
DAILY_DIR = STATE_DIR / 'daily'
REVISION_DIR = STATE_DIR / 'revisions'
STATE_DIR.mkdir(parents=True, exist_ok=True)
DAILY_DIR.mkdir(parents=True, exist_ok=True)
REVISION_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_STATE_FILE = STATE_DIR / 'current_state.json'


class ReuseServer(ThreadingHTTPServer):
    allow_reuse_address = True


class SPAHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def _json_response(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def _proxy_monitor(self):
        parsed = urlparse(self.path)
        if parsed.path == '/monitor':
            upstream_path = '/'
        elif parsed.path.startswith('/monitor/'):
            upstream_path = parsed.path[len('/monitor'):] or '/'
        elif parsed.path.startswith('/monitor-api/'):
            upstream_path = '/api/' + parsed.path[len('/monitor-api/'):]
        else:
            return False

        target = MONITOR_BASE.rstrip('/') + upstream_path
        if parsed.query:
            target += '?' + parsed.query

        body = None
        if self.command in {'POST', 'PUT', 'PATCH'}:
            length = int(self.headers.get('Content-Length', '0') or '0')
            body = self.rfile.read(length)

        req = Request(target, data=body, method=self.command)
        for name, value in self.headers.items():
            lname = name.lower()
            if lname in {'host', 'content-length', 'accept-encoding', 'connection'}:
                continue
            req.add_header(name, value)

        try:
            with urlopen(req, timeout=20) as resp:
                status = resp.status
                content = resp.read()
                content_type = resp.headers.get('Content-Type', 'application/octet-stream')
                headers = resp.headers
        except HTTPError as exc:
            status = exc.code
            content = exc.read()
            content_type = exc.headers.get('Content-Type', 'text/plain; charset=utf-8')
            headers = exc.headers
        except URLError as exc:
            self._json_response({'ok': False, 'error': f'monitor upstream unavailable: {exc.reason}'}, status=502)
            return True

        if parsed.path.startswith('/monitor') and 'text/html' in content_type:
            text = content.decode('utf-8', errors='ignore')
            text = text.replace('/api/', '/monitor-api/')
            content = text.encode('utf-8')

        self.send_response(status)
        skip_headers = {'content-length', 'transfer-encoding', 'connection', 'server', 'date'}
        for name, value in headers.items():
            if name.lower() in skip_headers:
                continue
            self.send_header(name, value)
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)
        return True

    def _read_json(self, path: Path):
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return None

    def _wrap_state(self, payload):
        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone()
        return {
            'saved_at': now_utc.isoformat(),
            'saved_at_local': now_local.isoformat(),
            'date': now_local.strftime('%Y-%m-%d'),
            'state': payload,
        }

    def _state_digest(self, wrapped):
        state_json = json.dumps(wrapped.get('state'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(state_json.encode('utf-8')).hexdigest()

    def _save_state(self, payload):
        wrapped = self._wrap_state(payload)
        state_date = wrapped['date']
        daily_file = DAILY_DIR / f'{state_date}.json'
        revision_day_dir = REVISION_DIR / state_date
        revision_day_dir.mkdir(parents=True, exist_ok=True)

        digest = self._state_digest(wrapped)
        last_digest = None
        current = self._read_json(CURRENT_STATE_FILE)
        if current:
            last_digest = current.get('digest') or self._state_digest(current)

        wrapped['digest'] = digest
        CURRENT_STATE_FILE.write_text(json.dumps(wrapped, ensure_ascii=False, indent=2), encoding='utf-8')
        daily_file.write_text(json.dumps(wrapped, ensure_ascii=False, indent=2), encoding='utf-8')

        if digest != last_digest:
            stamp = datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f')
            revision_file = revision_day_dir / f'{stamp}.json'
            revision_file.write_text(json.dumps(wrapped, ensure_ascii=False, indent=2), encoding='utf-8')

        return wrapped

    def _history_payload(self):
        history = []
        for daily_file in sorted(DAILY_DIR.glob('????-??-??.json'), reverse=True):
            payload = self._read_json(daily_file) or {}
            date = daily_file.stem
            revision_count = len(list((REVISION_DIR / date).glob('*.json')))
            history.append({
                'date': date,
                'saved_at': payload.get('saved_at'),
                'saved_at_local': payload.get('saved_at_local'),
                'revision_count': revision_count,
            })
        return {'history': history}

    def _revision_payload(self, date):
        if not date:
            return {'revisions': []}
        revision_day_dir = REVISION_DIR / date
        revisions = []
        if revision_day_dir.exists():
            for file in sorted(revision_day_dir.glob('*.json'), reverse=True):
                payload = self._read_json(file) or {}
                revisions.append({
                    'id': file.stem,
                    'saved_at': payload.get('saved_at'),
                    'saved_at_local': payload.get('saved_at_local'),
                })
        return {'date': date, 'revisions': revisions}

    def _load_wrapped_state(self, date=None, revision=None):
        if revision and date:
            return self._read_json(REVISION_DIR / date / f'{revision}.json')
        if date:
            return self._read_json(DAILY_DIR / f'{date}.json')
        return self._read_json(CURRENT_STATE_FILE)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/monitor'):
            if self._proxy_monitor():
                return
        if parsed.path == '/api/state':
            query = parse_qs(parsed.query)
            date = query.get('date', [None])[0]
            revision = query.get('revision', [None])[0]
            payload = self._load_wrapped_state(date=date, revision=revision) or {
                'saved_at': None,
                'saved_at_local': None,
                'date': date,
                'state': None,
            }
            return self._json_response(payload)
        if parsed.path == '/api/history':
            return self._json_response(self._history_payload())
        if parsed.path == '/api/revisions':
            query = parse_qs(parsed.query)
            date = query.get('date', [None])[0]
            return self._json_response(self._revision_payload(date))
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/monitor-api/'):
            if self._proxy_monitor():
                return
        if parsed.path != '/api/state':
            self.send_error(404, 'Not found')
            return
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode('utf-8'))
        except Exception:
            self.send_error(400, 'Invalid JSON')
            return
        wrapped = self._save_state(payload)
        return self._json_response({
            'ok': True,
            'saved_at': wrapped['saved_at'],
            'saved_at_local': wrapped['saved_at_local'],
            'date': wrapped['date'],
            'digest': wrapped['digest'],
        })

    def send_head(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/monitor'):
            return None
        if parsed.path.startswith('/api/'):
            self.send_error(404, 'Not found')
            return None
        path = self.translate_path(parsed.path)
        candidate = Path(path)
        if parsed.path in ('', '/') or not candidate.exists():
            self.path = '/index.html'
        else:
            self.path = parsed.path
        return super().send_head()


httpd = ReuseServer(('0.0.0.0', PORT), lambda *args, **kwargs: SPAHandler(*args, directory=str(ROOT), **kwargs))
print(f'Serving SPA whiteboard at http://0.0.0.0:{PORT}/ from {ROOT}', flush=True)
httpd.serve_forever()
