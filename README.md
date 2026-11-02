# PrismFlow

A real-time streaming analytics dashboard built with **Perspective**, **FastAPI**, and **React + TypeScript + Vite**:
- **Backend (`backend/`)**: Python + FastAPI + `perspective-python` hosting a virtual ring-buffer table (`market_trades`, 5,000-row limit) streamed over WebSockets via `PerspectiveStarletteHandler`, protected by `HttpOnly` JWT cookie authentication (`auth.py`).
- **Frontend (`frontend/`)**: React + TypeScript + Vite + React Router + `@perspective-dev/viewer` (`<perspective-viewer>`) with protected routes, login page (`/login`), preset layouts, and interactive stream controls.
- **Docker**: Separate `Dockerfile`s for `backend` and `frontend` orchestrated via `docker-compose.yml`.

## Authentication & Demo Accounts

Unauthenticated visitors are redirected to `/login`. Upon sign-in, the backend verifies credentials against the external auth service adapter (`verify_credentials_with_external_service` in `backend/auth.py`) and sets a signed JWT in an `HttpOnly`, `SameSite=Lax` cookie (`prismflow_access_token`) used to authenticate both REST (`/api/*`) and Perspective WebSocket (`/ws`) requests.

Built-in demo accounts (when `EXTERNAL_AUTH_URL` is not set):
- **Trader**: `trader` / `crypto2026`
- **Admin**: `admin` / `prismflow123`

## Project Structure

```text
prismflow/
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── index.html
│   ├── nginx.conf
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.css
│       ├── App.tsx
│       ├── main.tsx
│       └── vite-env.d.ts
└── docker-compose.yml
```

## Quick Start (Docker Compose)

Build and run both services:

```bash
docker compose up --build
```

- **Frontend UI**: http://localhost:5173
- **Backend API & Docs**: http://localhost:8000/docs
- **Backend Perspective WebSocket**: `ws://localhost:8000/ws` (also proxied at `ws://localhost:5173/ws`)

## Running Locally (Without Docker)

### 1. Start the Python Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start the Vite Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite automatically proxies `/api` and `/ws` to `http://localhost:8000`.
