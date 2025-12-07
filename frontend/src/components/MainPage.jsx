// src/MainPage.jsx
import React, { useState } from "react";
import { ThumbsUp, MessageSquare, Repeat, Send } from "lucide-react";
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
  const [posting, setPosting] = useState(false); // new: posting state for publish action
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
        } catch (e) {
          /* ignore parse error */
        }
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

  // Modified: clears fields on success, alerts user, and tracks posting state
  async function postToLinkedIn(text) {
    setPosting(true);
    try {
      const res = await fetch("/api/linkedin_post", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      // show full body for debugging when not ok
      const bodyText = await res.text();

      if (!res.ok) {
        throw new Error(
          `LinkedIn post failed: ${res.status} ${res.statusText} - ${bodyText}`
        );
      }

      // try parse JSON if server returns json
      let parsed;
      try {
        parsed = JSON.parse(bodyText);
      } catch {
        parsed = { success: true, raw: bodyText };
      }

      // SUCCESS: clear all fields and notify user
      handleReset();
      alert("Post published successfully on LinkedIn!");

      return parsed;
    } catch (err) {
      console.error("postToLinkedIn error:", err);
      alert("Failed to post on LinkedIn. Check console for details.");
      throw err;
    } finally {
      setPosting(false);
    }
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
              {/* <button
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
              </button> */}
            </div>

            <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
              <button className="button" type="submit" disabled={loading}>
                {loading ? "Generating..." : "Generate"}
              </button>
              <button
                type="button"
                className="button-outline"
                onClick={handleReset}
                disabled={loading || posting}
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
              <div style={{ textAlign: "center", color: "#666" }}>Generating…</div>
            ) : generated ? (
              <div className="linkedin-post">
                {/* Header */}
                <div className="linkedin-header">
                  <div className="linkedin-avatar">H</div>
                  <div className="linkedin-info">
                    <div className="linkedin-name">Herth</div>
                    <div className="linkedin-headline">Marketing & Growth • 1h</div>
                    <div className="linkedin-time">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 16 16"
                        data-supported-dps="16x16"
                        fill="currentColor"
                        width="16"
                        height="16"
                        focusable="false"
                      >
                        <path d="M8 1a7 7 0 107 7 7 7 0 00-7-7zM8 14A6 6 0 1114 8a6 6 0 01-6 6zm0-11a5 5 0 105 5 5 5 0 00-5-5zm.5 2h-1v3.5l2.5 1.5.5-.8-2-1.2V5z"></path>
                      </svg>
                    </div>
                  </div>
                </div>

                {/* Body */}
                <div className="linkedin-body">
                  {generated.post_title && (
                    <div style={{ fontWeight: "bold", marginBottom: 8 }}>
                      {generated.post_title}
                    </div>
                  )}
                  {generated.post_text}
                  {generated.post_hashtags?.length > 0 && (
                    <div className="linkedin-hashtags" style={{ marginTop: 8 }}>
                      {generated.post_hashtags.map((h) => (
                        <span key={h} style={{ marginRight: 4 }}>
                          #{h.replace(/^#/, "")}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Stats (Fake) */}
                <div className="linkedin-stats">
                  <span className="linkedin-stats-icon">👍 👏 ❤️</span>
                  <span style={{ marginLeft: 4 }}>88</span>
                  <span style={{ marginLeft: "auto" }}>4 comments • 1 repost</span>
                </div>

                {/* Footer Actions */}
                <div className="linkedin-footer">
                  <div className="linkedin-action">
                    <ThumbsUp size={18} />
                    <span>Like</span>
                  </div>
                  <div className="linkedin-action">
                    <MessageSquare size={18} />
                    <span>Comment</span>
                  </div>
                  <div className="linkedin-action">
                    <Repeat size={18} />
                    <span>Repost</span>
                  </div>
                  <div className="linkedin-action">
                    <Send size={18} />
                    <span>Send</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="preview-empty">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path
                    d="M3 7h18M3 12h18M3 17h10"
                    stroke="#9AA4B2"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <div>Generate content to see preview</div>
              </div>
            )}
          </div>

          {/* Action Buttons below preview */}
          {generated && (
            <div className="preview-actions">
              <button className="btn-secondary" onClick={handleCopy}>
                Copy Text
              </button>
              <button
                className="btn-primary"
                disabled={!generated?.post_text || posting}
                onClick={async () => {
                  if (!generated?.post_text) return;
                  try {
                    await postToLinkedIn(generated.post_text);
                  } catch (e) {
                    /* error already handled */
                  }
                }}
              >
                {posting ? "Posting..." : "Post to LinkedIn"}
              </button>
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}
