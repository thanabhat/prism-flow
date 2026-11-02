import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import random
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import perspective
from perspective.handlers.starlette import PerspectiveStarletteHandler
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Perspective Server & Virtual Table Setup
# ---------------------------------------------------------------------------
perspective_server = perspective.Server()
local_client = perspective_server.new_local_client()

TABLE_NAME = "market_trades"
TABLE_LIMIT = 5000

SCHEMA = {
    "id": "integer",
    "timestamp": "datetime",
    "symbol": "string",
    "sector": "string",
    "desk": "string",
    "side": "string",
    "price": "float",
    "quantity": "float",
    "notional": "float",
    "pnl": "float",
    "spread_bps": "float",
}

trades_table = local_client.table(SCHEMA, limit=TABLE_LIMIT, name=TABLE_NAME)

# ---------------------------------------------------------------------------
# Crypto Market Data Simulator State
# ---------------------------------------------------------------------------
SYMBOLS: dict[str, dict[str, Any]] = {
    "BTC-USD": {"sector": "Store of Value", "base_price": 94500.00, "lots": [0.05, 0.1, 0.25, 0.5, 1.0, 2.5]},
    "ETH-USD": {"sector": "Smart Contracts (L1)", "base_price": 3280.00, "lots": [0.5, 1.0, 2.5, 5.0, 10.0, 25.0]},
    "SOL-USD": {"sector": "Smart Contracts (L1)", "base_price": 212.50, "lots": [5.0, 10.0, 25.0, 50.0, 100.0, 250.0]},
    "BNB-USD": {"sector": "Smart Contracts (L1)", "base_price": 645.00, "lots": [1.0, 5.0, 10.0, 25.0, 50.0]},
    "SUI-USD": {"sector": "Smart Contracts (L1)", "base_price": 3.45, "lots": [250.0, 500.0, 1000.0, 2500.0, 5000.0]},
    "AVAX-USD": {"sector": "Smart Contracts (L1)", "base_price": 34.80, "lots": [25.0, 50.0, 100.0, 250.0, 500.0]},
    "ADA-USD": {"sector": "Smart Contracts (L1)", "base_price": 0.98, "lots": [1000.0, 2500.0, 5000.0, 10000.0, 25000.0]},
    "XRP-USD": {"sector": "Payments", "base_price": 2.42, "lots": [500.0, 1000.0, 2500.0, 5000.0, 10000.0]},
    "LINK-USD": {"sector": "DeFi & Infrastructure", "base_price": 18.60, "lots": [50.0, 100.0, 250.0, 500.0, 1000.0]},
    "UNI-USD": {"sector": "DeFi & Infrastructure", "base_price": 11.40, "lots": [100.0, 250.0, 500.0, 1000.0, 2000.0]},
    "DOGE-USD": {"sector": "Meme", "base_price": 0.36, "lots": [2500.0, 5000.0, 10000.0, 25000.0, 50000.0]},
}

DESKS = ["Spot-Global", "Perp-DeltaOne", "DeFi-Arb", "Basis-Quant", "Options-Vol"]
SIDES = ["BUY", "SELL"]


class StreamState:
    def __init__(self) -> None:
        self.streaming: bool = True
        self.interval_ms: int = 250
        self.batch_size: int = 8
        self.next_id: int = 1
        self.total_generated: int = 0
        self.current_prices: dict[str, float] = {
            sym: info["base_price"] for sym, info in SYMBOLS.items()
        }


state = StreamState()


def generate_trades(count: int, start_time: datetime | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    now = start_time or datetime.now(timezone.utc)

    for i in range(count):
        symbol = random.choice(list(SYMBOLS.keys()))
        info = SYMBOLS[symbol]

        # Random walk price
        drift = random.gauss(0, 0.003)
        new_price = max(0.0001, state.current_prices[symbol] * (1.0 + drift))
        state.current_prices[symbol] = new_price

        price = round(new_price, 4 if new_price < 10.0 else 2)
        quantity = float(random.choice(info["lots"]))
        notional = round(price * quantity, 2)
        side = random.choice(SIDES)
        spread_bps = round(random.uniform(0.5, 12.0), 2)
        pnl = round(random.gauss(15.0, 220.0), 2)
        ts = now + timedelta(milliseconds=i * 15)

        rows.append(
            {
                "id": state.next_id,
                "timestamp": ts,
                "symbol": symbol,
                "sector": info["sector"],
                "desk": random.choice(DESKS),
                "side": side,
                "price": price,
                "quantity": quantity,
                "notional": notional,
                "pnl": pnl,
                "spread_bps": spread_bps,
            }
        )
        state.next_id += 1
        state.total_generated += 1

    return rows


def seed_initial_data(initial_count: int = 400) -> None:
    start_ts = datetime.now(timezone.utc) - timedelta(minutes=10)
    batch = generate_trades(initial_count, start_time=start_ts)
    trades_table.update(batch)


async def stream_worker() -> None:
    """Background coroutine that streams simulated market trades into Perspective."""
    while True:
        if state.streaming:
            batch = generate_trades(state.batch_size)
            trades_table.update(batch)
        await asyncio.sleep(max(0.05, state.interval_ms / 1000.0))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed_initial_data(400)
    task = asyncio.create_task(stream_worker())
    try:
        yield
    finally:
        task.cancel()


# ---------------------------------------------------------------------------
# FastAPI App & Routes
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PrismFlow Backend",
    description="Real-time streaming Perspective server powered by FastAPI & WebSockets",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StreamConfigPayload(BaseModel):
    streaming: bool | None = None
    interval_ms: int | None = None
    batch_size: int | None = None


@app.get("/api/status")
async def get_status() -> dict[str, Any]:
    return {
        "table_name": TABLE_NAME,
        "table_limit": TABLE_LIMIT,
        "table_size": trades_table.size(),
        "total_generated": state.total_generated,
        "streaming": state.streaming,
        "interval_ms": state.interval_ms,
        "batch_size": state.batch_size,
    }


@app.post("/api/stream/config")
async def update_stream_config(payload: StreamConfigPayload) -> dict[str, Any]:
    if payload.streaming is not None:
        state.streaming = payload.streaming
    if payload.interval_ms is not None:
        state.interval_ms = max(50, min(5000, payload.interval_ms))
    if payload.batch_size is not None:
        state.batch_size = max(1, min(200, payload.batch_size))
    return await get_status()


@app.post("/api/table/burst")
async def trigger_burst(count: int = 250) -> dict[str, Any]:
    bounded = max(1, min(1000, count))
    trades_table.update(generate_trades(bounded))
    return await get_status()


@app.post("/api/table/reset")
async def reset_table() -> dict[str, Any]:
    trades_table.clear()
    state.next_id = 1
    state.total_generated = 0
    state.current_prices = {
        sym: info["base_price"] for sym, info in SYMBOLS.items()
    }
    seed_initial_data(200)
    return await get_status()


@app.websocket("/ws")
async def perspective_websocket(websocket: WebSocket) -> None:
    handler = PerspectiveStarletteHandler(
        perspective_server=perspective_server,
        websocket=websocket,
    )
    try:
        await handler.run()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
