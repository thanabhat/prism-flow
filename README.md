# PrismFlow

A real-time dashboard for simulated crypto trades, built with **React + TypeScript + Vite**, **FastAPI**, and **Perspective**.

**[Live demo →](https://prismflow.thanabh.at/)** · [API docs](https://prismflow-api.thanabh.at/docs)

## Try the Demo

Choose a quick-fill account on the login page, then click **Sign In**.

| Account | Username | Password |
| --- | --- | --- |
| Trader | `trader` | `crypto2026` |
| Admin | `admin` | `prismflow123` |

These are public demo accounts. All visitors share the same simulated stream,
including pause and reset controls. Data resets when the backend restarts.

## Features

- Live trades over WebSockets with a 5,000-row ring buffer.
- Trade blotter, sector/symbol pivot, exposure charts, and treemap layouts.
- Pause, resume, adjust speed, add bursts, or reset the stream.
- HttpOnly JWT cookie authentication with an optional external auth service.

## Run Locally

### With Docker

```bash
docker compose up --build
```

### Without Docker

Use Python 3.14 and Node.js 26. Open two terminals from the repo root.

**Terminal 1 — backend:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — frontend:**

```bash
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` and `/ws` to the backend on port 8000.

Open [localhost:5173](http://localhost:5173). Local API docs are at
[localhost:8000/docs](http://localhost:8000/docs).

Source: [frontend](frontend/) · [backend](backend/).

## Deployment

[render.yaml](render.yaml) defines separate frontend and API services on Render Free.
Choose **New → Blueprint**, connect this repo, then configure the custom domain DNS.
Render generates the JWT secret; keep private credentials in its environment settings.
See the [backend](backend/.env.example) and [frontend](frontend/.env.example) environment examples for configuration.

The free API may take about a minute to wake after inactivity.

## Checks

With dependencies installed:

```bash
python -m unittest discover -s backend/tests -v
npm --prefix frontend run build
```
