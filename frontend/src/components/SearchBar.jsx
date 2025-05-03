import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function SearchBar() {
  const [q, setQ] = useState("");
  const nav = useNavigate();

  return (
    <form
      onSubmit={e => {
        e.preventDefault();
        nav(`/search?q=${encodeURIComponent(q)}`);
      }}
    >
      <input value={q} onChange={e => setQ(e.target.value)} placeholder="search pins…" />
      <button>Go</button>
    </form>
  );
}

