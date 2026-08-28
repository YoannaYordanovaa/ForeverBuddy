import React, { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import BrandLogo from "./BrandLogo";
import "./App.css";

const STORAGE_KEY = "foreverbuddy_conversations";

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function createNewConversation() {
  return {
    id: generateId(),
    title: "Нов разговор",
    messages: [
      {
        sender: "bot",
        text: "Здравей! Аз съм твоят **Forever***Buddy*. 🌿\n{config.welcomeMessage}",
      },
    ],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };
}

function groupByDate(conversations) {
  const now = Date.now();
  const oneDay = 86400000;
  const oneWeek = 7 * oneDay;
  const groups = { "Днес": [], "Вчера": [], "Тази седмица": [], "По-рано": [] };
  conversations.forEach((conv) => {
    const diff = now - conv.updatedAt;
    if (diff < oneDay) groups["Днес"].push(conv);
    else if (diff < 2 * oneDay) groups["Вчера"].push(conv);
    else if (diff < oneWeek) groups["Тази седмица"].push(conv);
    else groups["По-рано"].push(conv);
  });
  return groups;
}

// Quick actions и брандиране се зареждат от сървъра (config.py)
const DEFAULT_CONFIG = {
  namePart1:      "Forever",
  namePart2:      "Buddy",
  brandColor:     "#6A0DAD",
  accentColor:    "#FFC300",
  headerBg:       "#2e0a47",
  welcomeMessage: "{config.welcomeMessage}",
  disclaimer:     "Това приложение е разработено с академична цел.",
  quickActions: [
    { icon: "🔍", label: "Намери продукт",  desc: "Цена, съставки и ползи",        prompt: "Помогни ми да намеря продукт." },
    { icon: "📱", label: "Напиши пост",     desc: "За Instagram, Facebook и др.",  prompt: "Напиши маркетингов пост за социални мрежи." },
    { icon: "📋", label: "Фирмена политика",desc: "Правила, процедури, условия",   prompt: "Обясни ми фирмената политика." },
    { icon: "✍️", label: "Напиши статия",   desc: "Блог съдържание с SEO",         prompt: "Напиши блог статия." },
  ],
};

function QuickActions({ onAction, actions }) {
  return (
    <div className="quick-actions-wrapper">
      <p className="quick-actions-title">Как мога да ти помогна днес?</p>
      <div className="quick-actions-grid">
        {actions.map((action) => (
          <button
            key={action.label}
            className="qa-btn"
            onClick={() => onAction(action.prompt)}
          >
            <span className="qa-icon">{action.icon}</span>
            <span className="qa-label">{action.label}</span>
            <span className="qa-desc">{action.desc}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const el = document.createElement("textarea");
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <button className={`copy-btn ${copied ? "copied" : ""}`} onClick={handleCopy} title="Копирай">
      {copied ? "✓ Копирано" : "⎘ Копирай"}
    </button>
  );
}

export default function App() {
  const [config, setConfig] = React.useState(DEFAULT_CONFIG);

  // Зареждаме конфигурацията от сървъра при стартиране
  React.useEffect(() => {
    fetch("/config")
      .then((r) => r.json())
      .then((data) => setConfig({ ...DEFAULT_CONFIG, ...data }))
      .catch(() => {}); // При грешка използваме DEFAULT_CONFIG
  }, []);

  const [conversations, setConversations] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.length > 0) return parsed;
      }
    } catch {}
    return [createNewConversation()];
  });

  const [activeId, setActiveId] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.length > 0) return parsed[0].id;
      }
    } catch {}
    return null;
  });

  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth > 768);
  const [deletingId, setDeletingId] = useState(null);
  const messagesEndRef = useRef(null);
  const isMobile = () => window.innerWidth <= 768;

  const resolvedActiveId = activeId ?? conversations[0]?.id;
  const activeConversation = conversations.find((c) => c.id === resolvedActiveId);
  const messages = activeConversation?.messages || [];
  const showQuickActions = messages.length === 1 && messages[0]?.sender === "bot";

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch {}
  }, [conversations]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const updateActiveConversation = useCallback(
    (updater) => {
      setConversations((prev) =>
        prev.map((conv) =>
          conv.id === resolvedActiveId
            ? { ...updater(conv), updatedAt: Date.now() }
            : conv
        )
      );
    },
    [resolvedActiveId]
  );

  const startNewConversation = () => {
    const newConv = createNewConversation();
    setConversations((prev) => [newConv, ...prev]);
    setActiveId(newConv.id);
    setInput("");
    if (isMobile()) setSidebarOpen(false);
  };

  const deleteConversation = (id, e) => {
    e.stopPropagation();
    setDeletingId(id);
    setTimeout(() => {
      setConversations((prev) => {
        const filtered = prev.filter((c) => c.id !== id);
        if (id === resolvedActiveId) {
          if (filtered.length > 0) setActiveId(filtered[0].id);
          else {
            const newConv = createNewConversation();
            setActiveId(newConv.id);
            setDeletingId(null);
            return [newConv];
          }
        }
        setDeletingId(null);
        return filtered.length > 0 ? filtered : [createNewConversation()];
      });
    }, 300);
  };

  const getHistory = useCallback(() => {
    const history = [];
    const msgs = activeConversation?.messages || [];
    for (let i = 1; i < msgs.length - 1; i += 2) {
      if (msgs[i].sender === "user" && msgs[i + 1]?.sender === "bot") {
        history.push([msgs[i].text, msgs[i + 1].text]);
      }
    }
    return history;
  }, [activeConversation]);

  const handleSend = useCallback(
    async (userText) => {
      if (!userText.trim() || isLoading) return;
      setIsLoading(true);

      updateActiveConversation((conv) => {
        const isFirst = conv.messages.filter((m) => m.sender === "user").length === 0;
        return {
          ...conv,
          title: isFirst
            ? userText.slice(0, 40) + (userText.length > 40 ? "…" : "")
            : conv.title,
          messages: [...conv.messages, { sender: "user", text: userText }],
        };
      });

      try {
        if (
          userText.toLowerCase().startsWith("/learn ") ||
          userText.toLowerCase().startsWith("/запомни ")
        ) {
          const fact = userText.replace(/^\/(learn|запомни)\s+/i, "");
          const res = await fetch("/learn", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: fact }),
          });
          if (!res.ok) throw new Error("Failed to learn");
          updateActiveConversation((conv) => ({
            ...conv,
            messages: [
              ...conv.messages,
              { sender: "bot", text: "✍️ **Разбрано!** Записах тази информация в базата данни." },
            ],
          }));
        } else if (
          userText.toLowerCase().startsWith("/forget ") ||
          userText.toLowerCase().startsWith("/забрави ")
        ) {
          const fact = userText.replace(/^\/(forget|забрави)\s+/i, "");
          const res = await fetch("/forget", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: fact }),
          });
          if (!res.ok) throw new Error("Failed to forget");
          const data = await res.json();
          updateActiveConversation((conv) => ({
            ...conv,
            messages: [
              ...conv.messages,
              { sender: "bot", text: `🗑️ **Операция памет:** ${data.message}` },
            ],
          }));
        } else {
          const history = getHistory();

          updateActiveConversation((conv) => ({
            ...conv,
            messages: [...conv.messages, { sender: "bot", text: "" }],
          }));

          const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: userText, history }),
          });

          if (!response.body) throw new Error("No response body");

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let done = false;
          let accumulated = "";
          const currentId = resolvedActiveId;

          while (!done) {
            const { value, done: doneReading } = await reader.read();
            done = doneReading;
            if (value) {
              accumulated += decoder.decode(value, { stream: true });
              const captured = accumulated;
              setConversations((prev) =>
                prev.map((conv) => {
                  if (conv.id !== currentId) return conv;
                  const msgs = [...conv.messages];
                  const last = msgs[msgs.length - 1];
                  if (last?.sender === "bot") {
                    msgs[msgs.length - 1] = { ...last, text: captured };
                  }
                  return { ...conv, messages: msgs, updatedAt: Date.now() };
                })
              );
            }
          }
        }
      } catch (error) {
        console.error("Error:", error);
        updateActiveConversation((conv) => ({
          ...conv,
          messages: [
            ...conv.messages,
            { sender: "bot", text: "⚠️ Грешка при връзката със сървъра." },
          ],
        }));
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, updateActiveConversation, getHistory, resolvedActiveId]
  );

  const sendFromInput = () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    handleSend(text);
  };

  const grouped = groupByDate(conversations);

  return (
    <div className="app-container">
      <aside className={`sidebar ${sidebarOpen ? "open" : "closed"}`}>
        <div className="sidebar-header">
          <BrandLogo namePart1={config.namePart1} namePart2={config.namePart2} accentColor={config.accentColor} />
          <button
            className="sidebar-toggle-btn"
            onClick={() => setSidebarOpen(false)}
            title="Затвори панела"
          >
            ✕
          </button>
        </div>

        <button className="new-chat-btn" onClick={startNewConversation}>
          <span>+</span> Нов разговор
        </button>

        <nav className="sidebar-nav">
          {Object.entries(grouped).map(([label, convs]) =>
            convs.length === 0 ? null : (
              <div key={label}>
                <div className="sidebar-section-label">{label}</div>
                {convs.map((conv) => (
                  <div
                    key={conv.id}
                    className={`sidebar-item ${conv.id === resolvedActiveId ? "active" : ""} ${deletingId === conv.id ? "deleting" : ""}`}
                    onClick={() => { setActiveId(conv.id); if (isMobile()) setSidebarOpen(false); }}
                  >
                    <span className="sidebar-item-title">{conv.title}</span>
                    <button
                      className="delete-btn"
                      onClick={(e) => deleteConversation(conv.id, e)}
                      title="Изтрий"
                    >
                      🗑
                    </button>
                  </div>
                ))}
              </div>
            )
          )}
        </nav>
      </aside>

      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      <div className="main-area">
        <header className="chat-header">
          {!sidebarOpen && (
            <button
              className="sidebar-open-btn"
              onClick={() => setSidebarOpen(true)}
              title="Отвори панела"
            >
              ☰
            </button>
          )}
          <img src="/Logo.png" alt="Logo" className="logo-img" />
        </header>

        <div className="chat-window">
          {messages.map((msg, index) => (
            <div key={index} className={`message-row ${msg.sender}`}>
              <div className={`bubble ${msg.sender}`}>
                {msg.sender === "bot" && (
                  <div className="bot-name">
                    <img src="/Icon.svg" alt="Avatar" className="bot-avatar" />
                    <strong style={{ color: config.brandColor }}>{config.namePart1}</strong>
                    <strong style={{ color: config.accentColor }}>{config.namePart2}</strong>
                  </div>
                )}
                {index === 0 ? (
                  <>
                    <span>
                      Здравей! Аз съм твоят{" "}
                      <strong style={{ color: config.brandColor }}>{config.namePart1}</strong>
                      <strong style={{ color: config.accentColor }}>{config.namePart2}</strong>.{" "}
                      {config.welcomeMessage}
                    </span>
                    {showQuickActions && (
                      <QuickActions onAction={handleSend} actions={config.quickActions} />
                    )}
                  </>
                ) : msg.sender === "bot" && msg.text === "" ? (
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                ) : (
                  <>
                    <ReactMarkdown>{msg.text}</ReactMarkdown>
                    {msg.sender === "bot" && msg.text && (
                      <CopyButton text={msg.text} />
                    )}
                  </>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <div className="input-wrapper">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendFromInput()}
              placeholder="Попитай нещо..."
              disabled={isLoading}
            />
            <button
              className="send-btn"
              onClick={sendFromInput}
              disabled={isLoading || !input.trim()}
            >
              ➤
            </button>
          </div>
        </div>

        <footer className="app-footer">
          {config.disclaimer}
        </footer>
      </div>
    </div>
  );
}