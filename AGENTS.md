# AGENTS.md

## Cursor Cloud specific instructions

### Project Overview

Reedies' Mahjong — a real-time multiplayer Sichuan Mahjong web game. Django backend (Channels/Daphne for WebSocket) + React frontend (CRA). SQLite database (file-based, no separate process). See `README.md` for full description.

### Services

| Service | Port | Command |
|---------|------|---------|
| Django backend (ASGI) | 8000 | `python3 manage.py runserver 0.0.0.0:8000` (from repo root) |
| React frontend (CRA) | 3000 | `BROWSER=none npm start` (from `frontend/`) |

Both must run simultaneously for full functionality. The frontend connects to backend via WebSocket at `ws://localhost:8000/ws/socket-server`.

### Key Caveats

- `python3-dev` and `libffi-dev` system packages are required to build the `cffi` dependency. These are already installed in the VM image.
- The channel layer uses `InMemoryChannelLayer` by default — Redis is **not required** for development.
- The `db.sqlite3` file is committed to the repo with migrations already applied. Running `python3 manage.py migrate` is safe and idempotent.
- The frontend test suite (`npm test`) has a pre-existing failure due to `require.context` (webpack-specific API unavailable in Jest). This is not a regression.
- ESLint is configured via CRA defaults (`react-app`, `react-app/jest`). Run with `npx eslint src/` from `frontend/`. Pre-existing lint errors exist only in `App.test.js`.
- The REST API root is at `/api/` (endpoints: `/api/room/`, `/api/player/`).
- `ALLOWED_HOSTS` is empty in settings, which works when `DEBUG=True`. If switching `DEBUG=False`, add `localhost` / `0.0.0.0`.
