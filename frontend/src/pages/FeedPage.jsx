import React, { useEffect, useState } from "react";
import API from "../api";
import PinCard from "../components/PinCard";

export default function FeedPage() {
  const [pins, setPins] = useState([]);

  useEffect(() => {
    API.get("/feed").then(res => setPins(res.data));
  }, []);

  return (
    <div>
      <h2>Feed</h2>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 20 }}>
        {pins.map(p => <PinCard key={p.pin_id} pin={p} />)}
      </div>
    </div>
  );
}


