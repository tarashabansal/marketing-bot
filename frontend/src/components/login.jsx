import React, { useState } from "react";
import "../index.css";

export default function Login({ onLogin, goToSignup }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    onLogin?.({ email, password });
  }

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <h2 style={{ margin: 0 }}>Login</h2>

        <form className="auth-form" onSubmit={handleSubmit}>
          <input
            className="input"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <input
            className="input"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button className="button" type="submit">Login</button>
        </form>

        <div style={{ marginTop: 14 }}>
          <button
            className="link-button"
            type="button"
            onClick={goToSignup}
            aria-label="Create account"
          >
            New here? Create account
          </button>
        </div>
      </div>
    </div>
  );
}
