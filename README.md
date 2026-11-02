# PrismFlow

A real-time streaming analytics dashboard built with **Perspective**, **FastAPI**, and **React + TypeScript + Vite**:
- **Backend (`backend/`)**: Python + FastAPI + `perspective-python` hosting a virtual ring-buffer table (`market_trades`, 5,000-row limit) streamed over WebSockets via `PerspectiveStarletteHandler`.
- **Frontend (`frontend/`)**: React + TypeScript + Vite + `@perspective-dev/viewer` (`<perspective-viewer>`) with preset layouts (Live Blotter, Sector × Symbol Pivot, Desk Exposure Bar Chart, and Notional/PnL Treemap) and interactive stream controls.
- **Docker**: Separate `Dockerfile`s for `backend` and `frontend` orchestrated via `docker-compose.yml`.

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
