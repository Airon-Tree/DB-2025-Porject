import React, { useState } from "react";
import API from "../api";
import { useNavigate } from "react-router-dom";
import { Link } from "react-router-dom";

export default function LoginForm({ onSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const nav = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      const { data } = await API.post("/login", { email, password });
      onSuccess(data);          // lifts user up to <App/>
      nav("/");
    } catch (e) {
      setErr(e.response?.data?.error || "login failed");
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>Login</h2>
      {err && <p>{err}</p>}
      <input placeholder="email" value={email} onChange={e => setEmail(e.target.value)} />
      <input type="password" placeholder="password" value={password} onChange={e => setPassword(e.target.value)} />
      <button>Login</button>
      <p style={{ marginTop: 12 }}>
        Don't have an account?{" "}
        <Link to="/signup">Sign up here</Link>
      </p>
    </form>
  );
}

