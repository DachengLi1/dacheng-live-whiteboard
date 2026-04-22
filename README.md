# Dacheng Live Whiteboard

A whiteboard-style daily planning board with saved state, daily snapshots, and lightweight history.

## What is included
- Whiteboard UI (`index.html`, `workspace-v1.html`)
- Lightweight Python servers for static hosting and SPA/API hosting
- **Sanitized sample data only** in `state_backups/` and `calendar_snapshot.json`

## Privacy
This public copy intentionally ships with demo/sample state instead of real planning history.

## Run
```bash
python3 serve_spa.py
# open http://127.0.0.1:8788/
```

You can edit the sample JSON files under `state_backups/` or post new state to `/api/state`.
