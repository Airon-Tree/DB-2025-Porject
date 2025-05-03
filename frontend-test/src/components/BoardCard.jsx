import React from "react";
import { Link } from "react-router-dom";
export default function BoardCard({ board }) {
  return (
    <li>
      <Link to={`/boards/${board.board_id}`}>{board.name}</Link>
    </li>
  );
}

