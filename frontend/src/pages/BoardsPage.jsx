import React, { useEffect, useState } from "react";
import API from "../api";
import BoardCard from "../components/BoardCard";

export default function BoardsPage() {
  const [boards, setBoards] = useState([]);
  const [newB, setNewB] = useState({ name: "", description: "" });

  useEffect(() => {
    API.get("/api/me")                      // fix on backend's auth
       .then(({ data }) => API.get(`/users/${data.id}/boards`))
       .then(res => setBoards(res.data));
  }, []);

  async function create(e) {
    e.preventDefault();
    const { data } = await API.post("/boards", newB);
    setBoards([...boards, data]);
    setNewB({ name: "", description: "" });
  }

  return (
    <div>
      <h2>Your Boards</h2>
      <ul>{boards.map(b => <BoardCard key={b.board_id} board={b} />)}</ul>
      <h3>Create board</h3>
      <form onSubmit={create}>
        <input placeholder="name" value={newB.name} onChange={e => setNewB({ ...newB, name: e.target.value })} />
        <input placeholder="desc" value={newB.description} onChange={e => setNewB({ ...newB, description: e.target.value })} />
        <button>Create</button>
      </form>
    </div>
  );
}


