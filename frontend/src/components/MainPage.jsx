import React, { useState } from "react";
import "../index.css";

export default function MainPage({ user, onLogout }) {
  const [prompt, setPrompt] = useState("");
  const [tone, setTone] = useState("");
  const [audience, setAudience] = useState("");
  const [platforms, setPlatforms] = useState({
    linkedin: true,
    twitter: false,
    instagram: false,
    reddit: true,
  });
  const [generated, setGenerated] = useState(""); // placeholder for generated post

  function togglePlatform(key) {
    setPlatforms((p) => ({ ...p, [key]: !p[key] }));
  }

  function handleGenerate(e) {
    e.preventDefault();
    // UI only — placeholder behaviour
    const active = Object.keys(platforms).filter((k) => platforms[k]);
    setGenerated(
      `Platform(s): ${active.join(", ") || "None selected"}\n\nTone: ${tone || "—"}\nAudience: ${audience || "—"}\n\nPrompt:\n${prompt || "—"}\n\n(Generated content will appear here.)`
    );
  }

  return (
    <div className="main-root">
      <header className="main-header">
        <div>
          <h1 className="app-title">INFLUENCE OS</h1>
          <div className="app-subtitle">AI-Powered LinkedIn Content Generator</div>
        </div>

        <div className="header-actions">
          {user && <div className="user-pill">{user.email}</div>}
          <button className="btn-ghost" onClick={onLogout}>Logout</button>
        </div>
      </header>

      <main className="main-grid">
        <section className="left-card">
          <div className="card-title">Content Configuration</div>

          <form className="config-form" onSubmit={handleGenerate}>
            <label className="label">Prompt</label>
            <textarea
              className="textarea"
              placeholder="Describe the kind of post you want..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={6}
            />

            <label className="label">Target audience</label>
            <input
              className="input"
              placeholder="e.g., Tech professionals, Founders"
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
            />

            <label className="label">Post tone</label>
            <input
              className="input"
              placeholder="e.g., Professional, Casual, Inspirational"
              value={tone}
              onChange={(e) => setTone(e.target.value)}
            />

            <div className="label">Publish platforms</div>
            <div className="platform-row">
              <button
                type="button"
                className={`chip ${platforms.linkedin ? "chip-active" : ""}`}
                onClick={() => togglePlatform("linkedin")}
              >
                LinkedIn
              </button>

              <button
                type="button"
                className={`chip ${platforms.twitter ? "chip-active" : ""}`}
                onClick={() => togglePlatform("twitter")}
              >
                Twitter
              </button>

              <button
                type="button"
                className={`chip ${platforms.instagram ? "chip-active" : ""}`}
                onClick={() => togglePlatform("instagram")}
              >
                Instagram
              </button>
              <button
                type="button"
                className={`chip ${platforms.reddit ? "chip-active" : ""}`}
                onClick={() => togglePlatform("reddit")}
              >
                Reddit
              </button>
            </div>

            <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
              <button className="button" type="submit">Generate</button>
              <button
                type="button"
                className="button-outline"
                onClick={() => {
                  setPrompt("");
                  setTone("");
                  setAudience("");
                  setPlatforms({ linkedin: true, twitter: false, instagram: false });
                  setGenerated("");
                }}
              >
                Reset
              </button>
            </div>
          </form>
        </section>

        <aside className="right-card">
          <div className="card-title">Post Preview</div>
          <div className="preview-area">
            {generated ? (
              <pre className="preview-text">{generated}</pre>
            ) : (
              <div className="preview-empty">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M3 7h18M3 12h18M3 17h10" stroke="#9AA4B2" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <div>Generate content to see preview</div>
              </div>
            )}
          </div>

          <div className="preview-actions">
            <button className="btn-secondary" disabled={!generated}>Copy</button>
            <button className="btn-secondary" disabled={!generated}>Download</button>
            <button className="btn-primary" disabled={!generated}>Schedule / Post</button>
          </div>
        </aside>
      </main>
    </div>
  );
}
