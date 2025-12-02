import React, { useState } from "react";
import "../index.css";

export default function Signup({ onSignup, goToLogin }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    onSignup?.({ name, email, password });
  }

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <h2 style={{ margin: 0 }}>Create account</h2>

        <form className="auth-form" onSubmit={handleSubmit}>
          <input
            className="input"
            type="text"
            placeholder="Full name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

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

          <button className="button" type="submit">Create account</button>
        </form>

        <div style={{ marginTop: 14 }}>
          <button
            className="link-button"
            type="button"
            onClick={goToLogin}
            aria-label="Already have an account"
          >
            Already have an account? Login
          </button>
        </div>
      </div>
    </div>
  );
}
