import React, { useState } from "react";
import API from "../api";

export default function PinCard({ pin }) {
  const [liked, setLiked] = useState(false);

  const img = `http://localhost:5000/static/uploads/${pin.image_filename}`;

  async function toggleLike() {
    setLiked(!liked);
    await API({
      url: `/pins/${pin.pin_id}/like`,
      method: liked ? "DELETE" : "POST"
    });
  }

  return (
    <div style={{ width: 240 }}>
      <img src={img} alt={pin.title} width="100%" />
      <h4>{pin.title}</h4>
      <button onClick={toggleLike}>{liked ? "Unlike" : "Like"}</button>
    </div>
  );
}
