import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import API from "../api";
import PinCard from "../components/PinCard";

export default function BoardPinsPage() {
  const { bid } = useParams();
  const [pins, setPins] = useState([]);

  useEffect(() => {
    API.get(`/boards/${bid}/pins`).then(res => setPins(res.data));
  }, [bid]);

  return (
    <div>
      <h2>Pins</h2>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 20 }}>
        {pins.map(p => <PinCard key={p.pin_id} pin={p} />)}
      </div>
    </div>
  );
}


