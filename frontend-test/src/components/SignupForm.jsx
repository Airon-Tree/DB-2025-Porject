import React, { useState } from "react";
import API from "../api";
import { useNavigate } from "react-router-dom";

export default function SignupForm() {
  const [f, setF] = useState({ username: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const nav = useNavigate();

  async function submit(e) {
    e.preventDefault();
    try {
      await API.post("/signup", f);
      nav("/login");
    } catch (e) {
      setErr(e.response?.data?.error || "signup failed");
    }
  }

  return (
    <form onSubmit={submit}>
      <h2>Sign Up</h2>
      {err && <p>{err}</p>}
      <input placeholder="username" value={f.username} onChange={e => setF({ ...f, username: e.target.value })} />
      <input placeholder="email" value={f.email} onChange={e => setF({ ...f, email: e.target.value })} />
      <input type="password" placeholder="password" value={f.password} onChange={e => setF({ ...f, password: e.target.value })} />
      <button>Register</button>
    </form>
  );
}

