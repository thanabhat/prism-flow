import { useEffect, useRef, useState } from "react";
import perspective from "@perspective-dev/client";
import perspective_viewer, {
  type HTMLPerspectiveViewerElement,
  type PerspectiveViewerConfig,
} from "@perspective-dev/viewer";
import "@perspective-dev/viewer-datagrid";
import "@perspective-dev/viewer-charts";
import "@perspective-dev/viewer/dist/css/themes.css";
import CLIENT_WASM from "@perspective-dev/viewer/dist/wasm/perspective-viewer.wasm?url";
import "./App.css";

interface ServerStatus {
  table_name: string;
  table_limit: number;
  table_size: number;
  total_generated: number;
  streaming: boolean;
  interval_ms: number;
  batch_size: number;
}

type PresetKey = "blotter" | "pivot" | "bar" | "treemap";

const PRESETS: Record<
  PresetKey,
  { label: string; config: PerspectiveViewerConfig }
> = {
  blotter: {
    label: "Live Blotter",
    config: {
      plugin: "Datagrid",
      group_by: [],
      split_by: [],
      columns: [
        "id",
        "timestamp",
        "symbol",
        "sector",
        "desk",
        "side",
        "price",
        "quantity",
        "notional",
        "pnl",
        "spread_bps",
      ],
      sort: [["id", "desc"]],
      aggregates: {},
    },
  },
  pivot: {
    label: "Sector × Symbol Pivot",
    config: {
      plugin: "Datagrid",
      group_by: ["sector", "symbol"],
      split_by: ["side"],
      columns: ["quantity", "notional", "pnl", "price"],
      aggregates: {
        quantity: "sum",
        notional: "sum",
        pnl: "sum",
        price: "avg",
      },
      sort: [["notional", "desc"]],
    },
  },
  bar: {
    label: "Desk Exposure (Chart)",
    config: {
      plugin: "Y Bar",
      group_by: ["desk"],
      split_by: ["sector"],
      columns: ["notional"],
      aggregates: { notional: "sum" },
      sort: [["notional", "desc"]],
    },
  },
  treemap: {
    label: "Notional & PnL Treemap",
    config: {
      plugin: "Treemap",
      group_by: ["sector", "symbol"],
      split_by: [],
      columns: ["notional", "pnl"],
      aggregates: { notional: "sum", pnl: "sum" },
      sort: [],
    },
  },
};

let wasmInitPromise: Promise<void> | null = null;
function ensureViewerWasmInitialized(): Promise<void> {
  if (!wasmInitPromise) {
    wasmInitPromise = perspective_viewer
      .init_client(fetch(CLIENT_WASM))
      .then(() => undefined);
  }
  return wasmInitPromise;
}

function getApiBaseUrl(): string {
  return import.meta.env.VITE_BACKEND_HTTP_URL || "";
}

function getWsUrl(): string {
  if (import.meta.env.VITE_BACKEND_WS_URL) {
    return import.meta.env.VITE_BACKEND_WS_URL;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws`;
}

export function App() {
  const viewerRef = useRef<HTMLPerspectiveViewerElement | null>(null);
  const [connected, setConnected] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activePreset, setActivePreset] = useState<PresetKey>("blotter");
  const [status, setStatus] = useState<ServerStatus | null>(null);

  // Connect <perspective-viewer> to Python backend virtual table over WebSocket
  useEffect(() => {
    let cancelled = false;
    let wsClient: Awaited<ReturnType<typeof perspective.websocket>> | null =
      null;

    async function connectViewer() {
      try {
        setErrorMessage(null);
        await ensureViewerWasmInitialized();
        if (cancelled) return;

        wsClient = await perspective.websocket(getWsUrl());
        const remoteTable = await wsClient.open_table("market_trades");
        if (cancelled) return;

        const viewer = viewerRef.current;
        if (viewer) {
          await viewer.load(remoteTable);
          await viewer.restore({
            theme: "Pro Dark",
            ...PRESETS.blotter.config,
          });
          setConnected(true);
        }
      } catch (err) {
        if (!cancelled) {
          setErrorMessage(
            err instanceof Error
              ? err.message
              : "Failed to connect to Perspective Python backend"
          );
          setConnected(false);
        }
      }
    }

    connectViewer();

    return () => {
      cancelled = true;
      if (wsClient) {
        wsClient.terminate().catch(() => undefined);
      }
    };
  }, []);

  // Poll backend status metrics for the React header
  useEffect(() => {
    let active = true;

    async function fetchStatus() {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/status`);
        if (res.ok && active) {
          const data: ServerStatus = await res.json();
          setStatus(data);
        }
      } catch {
        // Ignore transient fetch errors while backend starts
      }
    }

    fetchStatus();
    const timer = window.setInterval(fetchStatus, 1500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  async function applyPreset(presetKey: PresetKey) {
    setActivePreset(presetKey);
    const viewer = viewerRef.current;
    if (viewer && connected) {
      await viewer.restore(PRESETS[presetKey].config);
    }
  }

  async function toggleStreaming() {
    if (!status) return;
    const res = await fetch(`${getApiBaseUrl()}/api/stream/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ streaming: !status.streaming }),
    });
    if (res.ok) {
      setStatus(await res.json());
    }
  }

  async function updateSpeed(intervalMs: number) {
    const res = await fetch(`${getApiBaseUrl()}/api/stream/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ interval_ms: intervalMs }),
    });
    if (res.ok) {
      setStatus(await res.json());
    }
  }

  async function sendBurst() {
    const res = await fetch(`${getApiBaseUrl()}/api/table/burst?count=250`, {
      method: "POST",
    });
    if (res.ok) {
      setStatus(await res.json());
    }
  }

  async function resetTable() {
    const res = await fetch(`${getApiBaseUrl()}/api/table/reset`, {
      method: "POST",
    });
    if (res.ok) {
      setStatus(await res.json());
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div>
            <div className="brand-title">PrismFlow</div>
            <div className="brand-subtitle">
              Real-Time Crypto Streaming Analytics (`market_trades`)
            </div>
          </div>
          <span
            className={`status-badge ${
              !connected
                ? "disconnected"
                : status?.streaming
                ? ""
                : "paused"
            }`}
          >
            <span className="pulse-dot" />
            {!connected
              ? "Connecting..."
              : status?.streaming
              ? "Live Streaming"
              : "Stream Paused"}
          </span>
        </div>

        <div className="toolbar">
          <div className="preset-group">
            {(Object.keys(PRESETS) as PresetKey[]).map((key) => (
              <button
                key={key}
                type="button"
                className={`btn ${activePreset === key ? "active" : ""}`}
                disabled={!connected}
                onClick={() => applyPreset(key)}
              >
                {PRESETS[key].label}
              </button>
            ))}
          </div>

          <div className="divider" />

          <div className="action-group">
            <button
              type="button"
              className="btn primary"
              disabled={!status}
              onClick={toggleStreaming}
            >
              {status?.streaming ? "Pause Stream" : "Resume Stream"}
            </button>
            <button
              type="button"
              className="btn"
              disabled={!status}
              onClick={sendBurst}
            >
              +250 Burst
            </button>
            <button
              type="button"
              className="btn"
              disabled={!status}
              onClick={resetTable}
            >
              Reset Table
            </button>
          </div>
        </div>
      </header>

      <div className="metrics-bar">
        <span className="metric-item">
          Active Rows in Ring Buffer:{" "}
          <strong>
            {status ? status.table_size.toLocaleString() : "—"} /{" "}
            {status ? status.table_limit.toLocaleString() : "5,000"}
          </strong>
        </span>
        <span className="metric-item">
          Total Generated Trades:{" "}
          <strong>
            {status ? status.total_generated.toLocaleString() : "—"}
          </strong>
        </span>
        <span className="metric-item">
          Batch Size:{" "}
          <strong>{status ? `${status.batch_size} rows/tick` : "—"}</strong>
        </span>
        <span className="metric-item">
          Tick Interval:{" "}
          <select
            className="speed-select"
            value={status?.interval_ms ?? 250}
            onChange={(e) => updateSpeed(Number(e.target.value))}
          >
            <option value={100}>100 ms (Fast)</option>
            <option value={250}>250 ms (Normal)</option>
            <option value={500}>500 ms (Relaxed)</option>
            <option value={1000}>1000 ms (Slow)</option>
          </select>
        </span>
      </div>

      <main className="viewer-container">
        {errorMessage && (
          <div className="overlay-banner">
            <div>⚠️ {errorMessage}</div>
            <div style={{ color: "#9ca3af", fontSize: "12px" }}>
              Ensure the Python FastAPI backend is running on port 8000.
            </div>
          </div>
        )}
        <perspective-viewer ref={viewerRef} theme="Pro Dark" />
      </main>
    </div>
  );
}

export default App;
