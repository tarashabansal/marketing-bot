// src/MainPage.jsx
import React, { useState } from "react";
import "../index.css";

export default function MainPage() {
  const [prompt, setPrompt] = useState("");
  const [tone, setTone] = useState("");
  const [audience, setAudience] = useState("");
  const [platforms, setPlatforms] = useState({
    linkedin: true,
    twitter: false,
    reddit: false,
  });
  const [generated, setGenerated] = useState(null); // { post_title, post_text, post_hashtags }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function togglePlatform(key) {
    setPlatforms((p) => ({ ...p, [key]: !p[key] }));
  }

  async function handleGenerate(e) {
    e?.preventDefault?.();
    setError("");
    setGenerated(null);
    setLoading(true);

    // payload expected by server: { prompt, tone, audience, plaforms, image_urls? }
    const payload = {
      prompt: prompt,
        tone: tone,
        audience: audience,
        selected_platforms: Object.keys(platforms).filter((k) => platforms[k]),
      // optionally send images later
      image_urls: [],
    };

    try {
      
      const backendUrl = "/api/generate";
      const res = await fetch(backendUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        // try to read server JSON message
        let errText = `Server returned ${res.status}`;
        try {
          const body = await res.json();
          errText = body.detail || body.error || JSON.stringify(body);
        } catch (e) { /* ignore parse error */ }
        throw new Error(errText);
      }

      const data = await res.json();

      if (!data || !data.post_text) {
        throw new Error("Invalid response from server");
      }

      setGenerated({
        post_title: data.post_title,
        post_text: data.post_text,
        post_hashtags: data.post_hashtags,
        polished_prompt: data.polished_prompt,
        platform: data.platform,
      });
    } catch (err) {
      console.error(err);
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setPrompt("");
    setTone("");
    setAudience("");
    setPlatforms({ linkedin: true, twitter: false, reddit: false });
    setGenerated(null);
    setError("");
  }

  async function handleCopy() {
    if (!generated?.post_text) return;
    try {
      await navigator.clipboard.writeText(generated.post_text);
      // small feedback — you can replace with toast
      alert("Copied post text to clipboard");
    } catch (err) {
      alert("Copy failed — please select and copy manually");
    }
  }

  function handleDownload() {
    if (!generated?.post_text) return;
    const contents = `${generated.post_title ? generated.post_title + "\n\n" : ""}${generated.post_text}\n\n${generated.post_hashtags?.length ? generated.post_hashtags.join(" ") : ""}`;
    const blob = new Blob([contents], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "generated_post.txt";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="main-root">
      <header className="main-header">
        <div>
          <h1 className="app-title">AutoPostly</h1>
          <div className="app-subtitle">Helping market your dreams</div>
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
                className={`chip ${platforms.reddit ? "chip-active" : ""}`}
                onClick={() => togglePlatform("reddit")}
              >
                Reddit
              </button>
            </div>

            <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
              <button className="button" type="submit" disabled={loading}>
                {loading ? "Generating..." : "Generate"}
              </button>
              <button
                type="button"
                className="button-outline"
                onClick={handleReset}
                disabled={loading}
              >
                Reset
              </button>
            </div>

            {error && <div style={{ color: "crimson", marginTop: 10 }}>{error}</div>}
          </form>
        </section>

        <aside className="right-card">
          <div className="card-title">Post Preview</div>

          <div className="preview-area">
            {loading ? (
              <div style={{ textAlign: "center" }}>Generating…</div>
            ) : generated ? (
              <div style={{ width: "100%", textAlign: "left" }}>
                {generated.post_title && (
                  <h3 style={{ marginTop: 0 }}>{generated.post_title}</h3>
                )}
                <pre className="preview-text" style={{ margin: 0 }}>
                  {generated.post_text}
                </pre>
                {generated.post_hashtags?.length > 0 && (
                  <div style={{ marginTop: 12, color: "#475569" }}>
                    {generated.post_hashtags.map((h) => (
                      <span key={h} style={{ marginRight: 8 }}>
                        #{h.replace(/^#/, "")}
                      </span>
                    ))}
                  </div>
                )}
                <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                  <button className="btn-secondary" onClick={handleCopy}>
                    Copy
                  </button>
                  <button className="btn-secondary" onClick={handleDownload}>
                    Download
                  </button>
                  <button className="btn-primary" disabled={!generated} onClick={() => alert("Schedule/Post not implemented yet")}>
                    Schedule / Post
                  </button>
                </div>
              </div>
            ) : (
              <div className="preview-empty">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M3 7h18M3 12h18M3 17h10" stroke="#9AA4B2" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <div>Generate content to see preview</div>
              </div>
            )}
          </div>
        </aside>
      </main>
    </div>
  );
}
