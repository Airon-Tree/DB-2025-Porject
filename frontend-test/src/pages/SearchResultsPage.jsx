import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import API from "../api";
import PinCard from "../components/PinCard";

export default function SearchResultsPage() {
  const loc = useLocation();
  const [pins, setPins] = useState([]);

  useEffect(() => {
    const q = new URLSearchParams(loc.search).get("q") || "";
    if (q) API.get(`/search?q=${encodeURIComponent(q)}`).then(res => setPins(res.data));
  }, [loc]);

  return (
    <div>
      <h2>Results</h2>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 20 }}>
        {pins.map(p => <PinCard key={p.pin_id} pin={p} />)}
      </div>
    </div>
  );
}


