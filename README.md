# PrismFlow

A real-time streaming analytics dashboard built with **Perspective**, **FastAPI**, and **React + TypeScript + Vite**:
- **Backend (`backend/`)**: Python + FastAPI + `perspective-python` hosting a virtual ring-buffer table (`market_trades`, 5,000-row limit) streamed over WebSockets via `PerspectiveStarletteHandler`, protected by `HttpOnly` JWT cookie authentication (`auth.py`).
- **Frontend (`frontend/`)**: React + TypeScript + Vite + React Router + `@perspective-dev/viewer` (`<perspective-viewer>`) with protected routes, login page (`/login`), preset layouts, and interactive stream controls.
- **Docker**: Separate `Dockerfile`s for `backend` and `frontend` orchestrated via `docker-compose.yml`.

## Live Demo

**[Open PrismFlow →](https://prismflow.thanabh.at/)**

1. Choose a **Trader** or **Admin** demo account on the login page, then click
   **Sign In**. The credentials are listed below.
2. Explore the live trade blotter, sector/symbol pivot, desk exposure chart, and
   treemap using the layout buttons.
3. Pause or resume the stream, change its speed, add a burst of trades, or reset
   the table.

All market data is simulated, and visitors share the same stream. The demo runs
on Render Free, so the first request after an idle period can take about a minute
while the API starts. In-memory trades reset when the backend restarts or redeploys.

## Authentication & Demo Accounts

Unauthenticated visitors are redirected to `/login`. Upon sign-in, the backend verifies credentials against the external auth service adapter (`verify_credentials_with_external_service` in `backend/auth.py`) and sets a signed JWT in an `HttpOnly`, `SameSite=Lax` cookie (`prismflow_access_token`) used to authenticate both REST (`/api/*`) and Perspective WebSocket (`/ws`) requests.

Built-in demo accounts (when `EXTERNAL_AUTH_URL` is not set):
- **Trader**: `trader` / `crypto2026`
- **Admin**: `admin` / `prismflow123`

These credentials are intentionally public demo accounts, also shown on the login
page. Anyone can sign in and change the shared simulated stream, including pausing
or resetting it. Connect `EXTERNAL_AUTH_URL` to your own authentication service if
you need restricted access.

## Project Structure

```text
prism-flow/
├── backend/
│   ├── .env.example
│   ├── Dockerfile
│   ├── auth.py
│   ├── main.py
│   ├── requirements.txt
│   └── tests/
│       └── test_deployment.py
├── frontend/
│   ├── .env.example
│   ├── Dockerfile
│   ├── index.html
│   ├── nginx.conf
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.css
│       ├── App.tsx
│       ├── auth/
│       │   └── AuthContext.tsx
│       ├── main.tsx
│       ├── pages/
│       │   └── LoginPage.tsx
│       └── vite-env.d.ts
├── docker-compose.yml
└── render.yaml
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

## Deploy separately on Render Free

The root `render.yaml` defines two independent services from this repo:

| Service | Type | Root directory | Custom domain |
| --- | --- | --- | --- |
| `prismflow-web` | Static Site | `frontend` | [prismflow.thanabh.at](https://prismflow.thanabh.at/) |
| `prismflow-api` | Free Web Service | `backend` | [prismflow-api.thanabh.at](https://prismflow-api.thanabh.at/docs) |

The deployed API exposes [interactive API docs](https://prismflow-api.thanabh.at/docs)
and a public [health check](https://prismflow-api.thanabh.at/healthz). Protected API
routes and WebSocket connections require the login cookie.

1. Push the repo, then choose **New > Blueprint** in Render and select it. Review
   the two services before creating the Blueprint. The API uses the Free compute
   plan; the frontend uses a free Static Site.
2. Render generates a private `JWT_SECRET` for the API. The backend refuses to
   start on Render or with `COOKIE_SECURE=true` unless this secret is configured
   with at least 32 bytes. Local development without a secret uses a random key
   per process, so restarting the backend signs out existing sessions.
3. In the DNS settings for `thanabh.at`, create CNAME records named `prismflow`
   and `prismflow-api`, pointing to the respective service's actual `onrender.com`
   hostname. Use the values shown in Render, without `https://` or a path.
4. Verify both custom domains in Render and wait for their HTTPS certificates.
   With Cloudflare DNS, use **DNS only** while verifying and issuing certificates.
5. Check `https://prismflow-api.thanabh.at/healthz`, then sign in at
   `https://prismflow.thanabh.at` and confirm that the stream and controls work.

For services created manually, copy the commands, domains, route, and environment
settings from `render.yaml`. Generate `JWT_SECRET` privately with
`openssl rand -hex 32` and set it in the API service's Environment settings.
Use `/healthz` as the API health check path. The frontend needs the `/*` to
`/index.html` rewrite for direct navigation and reloads on React Router routes.

`ALLOWED_ORIGINS` accepts a comma-separated list of frontend origins and controls
both HTTP CORS and browser WebSocket connections. On Render it allows only
`https://prismflow.thanabh.at`; the default also supports local development.
Both custom domains use HTTPS under `thanabh.at`, so requests are cross-origin
but same-site and the existing `SameSite=Lax` cookie works with credentialed
requests. Keep the login cookie scoped to the API host; no parent-domain cookie
setting is needed. Test sign-in through the custom frontend domain.

The `VITE_BACKEND_HTTP_URL` and `VITE_BACKEND_WS_URL` values are public build-time
settings. After changing them, rebuild and redeploy the frontend. `NODE_VERSION=26`
matches the frontend Docker build, and the native API runtime uses Python 3.14.
`.env.example` files document these settings; Vite can read a local `frontend/.env`.
For a local `backend/.env`, use `uvicorn main:app --reload --env-file .env` from
`backend/`, or export the variables in your shell.

Render Free can sleep after 15 minutes without inbound traffic, and the simulated
in-memory data resets on restarts or deploys. Run a single API worker because the
Perspective table and stream state are process-local.

Render references: [Blueprint specification](https://render.com/docs/blueprint-spec),
[custom domains](https://render.com/docs/custom-domains),
[free service limits](https://render.com/docs/free).

## Public repository configuration

The custom domains, deployment settings, `.env.example` files, and public demo
accounts can be committed. Keep real JWT keys, external authentication credentials,
and private keys in Render's Environment settings or ignored local files. Never
put secrets in `VITE_*` variables: they become part of the downloaded JavaScript.
Local `.env` variants and private key files are excluded by `.gitignore` and the
Docker build contexts.

## Verification

With backend dependencies installed, run the deployment and authentication checks:

```bash
python -m unittest discover -s backend/tests -v
```

For the frontend, run `npm run build` from `frontend/`.
