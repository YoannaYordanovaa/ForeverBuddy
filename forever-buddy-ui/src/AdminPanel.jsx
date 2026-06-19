import React, { useState, useEffect, useRef } from "react";
import "./AdminPanel.css";

const API = "http://localhost:8000";

export default function AdminPanel() {
  const [password, setPassword] = useState("");
  const [isAuth, setIsAuth] = useState(false);
  const [authError, setAuthError] = useState("");
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState(null);
  const [rebuilding, setRebuilding] = useState(false);
  const [rebuildLog, setRebuildLog] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);
  const logEndRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [rebuildLog]);

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API}/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        setIsAuth(true);
        setAuthError("");
        loadFiles(password);
      } else {
        setAuthError("Грешна парола. Опитай отново.");
      }
    } catch {
      setAuthError("Грешка при свързване със сървъра.");
    }
  };

  const loadFiles = async (pwd) => {
    try {
      const res = await fetch(`${API}/admin/files?password=${encodeURIComponent(pwd || password)}`);
      if (res.ok) {
        const data = await res.json();
        setFiles(data.files);
      }
    } catch {}
  };

  const handleUpload = async (fileList) => {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    setUploadMsg(null);
    const results = [];

    for (const file of Array.from(fileList)) {
      const formData = new FormData();
      formData.append("password", password);
      formData.append("file", file);
      try {
        const res = await fetch(`${API}/admin/upload`, {
          method: "POST",
          body: formData,
        });
        const data = await res.json();
        results.push({ name: file.name, ok: res.ok, msg: data.message || data.detail });
      } catch {
        results.push({ name: file.name, ok: false, msg: "Грешка при качване." });
      }
    }

    setUploading(false);
    const errors = results.filter((r) => !r.ok);
    if (errors.length === 0) {
      setUploadMsg({ type: "success", text: `✅ ${results.length} файл(а) качени успешно.` });
    } else {
      setUploadMsg({ type: "error", text: `⚠️ ${errors.length} файл(а) не са качени: ${errors.map(e => e.name).join(", ")}` });
    }
    loadFiles();
  };

  const handleDelete = async (filename) => {
    if (!window.confirm(`Изтриване на "${filename}"?`)) return;
    try {
      const res = await fetch(
        `${API}/admin/files/${encodeURIComponent(filename)}?password=${encodeURIComponent(password)}`,
        { method: "DELETE" }
      );
      if (res.ok) {
        setFiles((prev) => prev.filter((f) => f.name !== filename));
      }
    } catch {}
  };

  const startRebuild = async () => {
    setRebuilding(true);
    setRebuildLog(["⏳ Свързване..."]);
    try {
      const res = await fetch(`${API}/admin/rebuild`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) {
        const data = await res.json();
        setRebuildLog([`❌ ${data.detail}`]);
        setRebuilding(false);
        return;
      }
      // Polling за статус
      pollRef.current = setInterval(async () => {
        try {
          const sr = await fetch(
            `${API}/admin/rebuild/status?password=${encodeURIComponent(password)}`
          );
          if (sr.ok) {
            const sd = await sr.json();
            setRebuildLog(sd.log);
            if (!sd.running) {
              setRebuilding(false);
              clearInterval(pollRef.current);
            }
          }
        } catch {}
      }, 1500);
    } catch {
      setRebuildLog(["❌ Грешка при свързване."]);
      setRebuilding(false);
    }
  };

  const openFile = (filename) => {
    // Паролата се encode-ва като base64 — не се показва plain text в URL
    const token = btoa(unescape(encodeURIComponent(password)));
    const url = `${API}/admin/files/${encodeURIComponent(filename)}/download?token=${encodeURIComponent(token)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // ── LOGIN SCREEN ──────────────────────────────────────────
  if (!isAuth) {
    return (
      <div className="admin-login-wrap">
        <div className="admin-login-card">
          <div className="admin-login-logo">
            <span className="admin-logo-p1">Forever</span>
            <span className="admin-logo-p2">Buddy</span>
            <span className="admin-login-sub">Административен панел</span>
          </div>
          <form onSubmit={handleLogin} className="admin-login-form">
            <label className="admin-label">Администраторска парола</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Въведи парола..."
              className="admin-input"
              autoFocus
            />
            {authError && <div className="admin-error">{authError}</div>}
            <button type="submit" className="admin-btn-primary">
              Вход →
            </button>
          </form>
          <div className="admin-back-link">
            <a href="/">← Обратно към чатбота</a>
          </div>
        </div>
      </div>
    );
  }

  // ── ADMIN DASHBOARD ───────────────────────────────────────
  return (
    <div className="admin-wrap">
      <header className="admin-header">
        <div className="admin-header-left">
          <span className="admin-logo-p1">Forever</span>
          <span className="admin-logo-p2">Buddy</span>
          <span className="admin-header-title">Административен панел</span>
        </div>
        <div className="admin-header-right">
          <a href="/" className="admin-header-link">← Чатбот</a>
          <button className="admin-btn-ghost" onClick={() => setIsAuth(false)}>
            Изход
          </button>
        </div>
      </header>

      <main className="admin-main">

        {/* ── СЕКЦИЯ: ФАЙЛОВЕ ── */}
        <section className="admin-section">
          <div className="admin-section-header">
            <h2 className="admin-section-title">📁 Файлове в базата данни</h2>
            <button
              className="admin-btn-primary admin-btn-sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? "Качване..." : "+ Качи файлове"}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.xlsx,.xls,.json,.txt,.md"
              style={{ display: "none" }}
              onChange={(e) => handleUpload(e.target.files)}
            />
          </div>

          {/* Drag & drop зона */}
          <div
            className={`admin-dropzone ${dragOver ? "drag-over" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleUpload(e.dataTransfer.files);
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            <span className="admin-dropzone-icon">📂</span>
            <span className="admin-dropzone-text">
              Провлачи файлове тук или кликни за избор
            </span>
            <span className="admin-dropzone-sub">
              PDF, DOCX, XLSX, JSON, TXT, MD
            </span>
          </div>

          {uploadMsg && (
            <div className={`admin-msg admin-msg-${uploadMsg.type}`}>
              {uploadMsg.text}
            </div>
          )}

          {/* Таблица с файлове */}
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Файл</th>
                  <th>Размер</th>
                  <th>Променен</th>
                  <th></th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {files.length === 0 ? (
                  <tr>
                    <td colSpan="4" className="admin-table-empty">
                      Няма файлове в базата данни
                    </td>
                  </tr>
                ) : (
                  files.map((f) => (
                    <tr key={f.name}>
                      <td className="admin-filename">
                        <span className="admin-file-icon">
                          {f.name.endsWith(".pdf") ? "📄" :
                           f.name.endsWith(".json") ? "🗂" :
                           f.name.endsWith(".xlsx") || f.name.endsWith(".xls") ? "📊" :
                           f.name.endsWith(".docx") ? "📝" : "📃"}
                        </span>
                        {f.name}
                      </td>
                      <td className="admin-filesize">{formatSize(f.size)}</td>
                      <td className="admin-filedate">{f.modified}</td>
                      <td>
                        <button
                          className="admin-btn-view-sm"
                          onClick={() => openFile(f.name)}
                          title="Отвори"
                        >
                          👁
                        </button>
                      </td>
                      <td>
                        <button
                          className="admin-btn-danger-sm"
                          onClick={() => handleDelete(f.name)}
                          title="Изтрий"
                        >
                          🗑
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── СЕКЦИЯ: REBUILD ── */}
        <section className="admin-section">
          <div className="admin-section-header">
            <h2 className="admin-section-title">🔄 Обновяване на базата данни</h2>
          </div>
          <p className="admin-section-desc">
            След качване на нови файлове стартирай rebuild за да ги включиш в базата.
            Процесът минава през три стъпки: обработка на продукти → конвертиране → изграждане на векторна база.
          </p>
          <button
            className={`admin-btn-primary ${rebuilding ? "admin-btn-loading" : ""}`}
            onClick={startRebuild}
            disabled={rebuilding}
          >
            {rebuilding ? "⏳ Rebuild в ход..." : "🚀 Стартирай Rebuild"}
          </button>

          {rebuildLog.length > 0 && (
            <div className="admin-log">
              {rebuildLog.map((line, i) => (
                <div
                  key={i}
                  className={`admin-log-line ${
                    line.startsWith("🎉") ? "log-success" :
                    line.startsWith("❌") ? "log-error" :
                    line.startsWith("⚠️") ? "log-warn" :
                    line.startsWith("💡") ? "log-info" : ""
                  }`}
                >
                  {line}
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          )}
        </section>

        {/* ── СЕКЦИЯ: СТАТИСТИКА ── */}
        <section className="admin-section">
          <div className="admin-section-header">
            <h2 className="admin-section-title">📊 Статистика</h2>
          </div>
          <div className="admin-stats-grid">
            <div className="admin-stat-card">
              <div className="admin-stat-num">{files.length}</div>
              <div className="admin-stat-label">Файла в базата</div>
            </div>
            <div className="admin-stat-card">
              <div className="admin-stat-num">
                {files.filter(f => f.name.endsWith(".pdf")).length}
              </div>
              <div className="admin-stat-label">PDF файла</div>
            </div>
            <div className="admin-stat-card">
              <div className="admin-stat-num">
                {(files.reduce((acc, f) => acc + f.size, 0) / (1024 * 1024)).toFixed(1)} MB
              </div>
              <div className="admin-stat-label">Общ размер</div>
            </div>
            <div className="admin-stat-card">
              <div className="admin-stat-num">
                {files.filter(f => f.name.endsWith(".json")).length}
              </div>
              <div className="admin-stat-label">JSON файла</div>
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}