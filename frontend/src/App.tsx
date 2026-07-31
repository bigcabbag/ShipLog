import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "./api/health";
import ChatPanel from "./components/ChatPanel";
import UploadPanel from "./components/UploadPanel";
import { API_BASE_URL } from "./config";
import "./App.css";

type LoadState = "loading" | "ok" | "error";

function App() {
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetchHealth()
      .then((data) => {
        if (!cancelled) {
          setHealth(data);
          setLoadState("ok");
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "未知错误");
          setLoadState("error");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const backendReady = loadState === "ok";

  return (
    <div className="app-shell">
      <div className="app-shell__ambient" aria-hidden="true">
        <div className="app-shell__orb app-shell__orb--signal" />
        <div className="app-shell__orb app-shell__orb--live" />
        <div className="app-shell__grain" />
      </div>

      <main className="page">
        <header className="header">
          <div className="header__top">
            <div className="header__brand">
              <div className="header__mark" aria-hidden="true" />
              <div>
                <p className="eyebrow">ShipLog · On-call</p>
                <h1>故障排查助手</h1>
              </div>
            </div>
            <div className="header__meta">
              <span
                className={`status-pill status-pill--${loadState}`}
                title={API_BASE_URL || "同源反代"}
              >
                <span className="status-pill__dot" />
                {loadState === "loading" && "连接中"}
                {loadState === "ok" && (health?.message ?? "服务在线")}
                {loadState === "error" && (error ?? "后端离线")}
              </span>
            </div>
          </div>
          <p className="subtitle">
            Runbook · 混合检索 · CRAG · 截图读图 —{" "}
            <span className="header__api-hint">
              {API_BASE_URL || "API 同源反代"}
            </span>
          </p>
          {loadState === "error" && (
            <p className="hint">
              启动后端：<code>docker compose up -d</code> 或{" "}
              <code>.\scripts\dev.ps1</code>
            </p>
          )}
        </header>

        <div className="workspace">
          <div className="workspace__main">
            <ChatPanel disabled={!backendReady} />
          </div>
          <aside className="workspace__side">
            <UploadPanel disabled={!backendReady} />
          </aside>
        </div>
      </main>
    </div>
  );
}

export default App;
