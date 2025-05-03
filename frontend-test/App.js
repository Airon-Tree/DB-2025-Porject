import React, { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import LoginForm from "./components/LoginForm";
import SignupForm from "./components/SignupForm";
import SearchBar from "./components/SearchBar";
import FeedPage from "./pages/FeedPage";
import BoardsPage from "./pages/BoardsPage";
import BoardPinsPage from "./pages/BoardPinsPage";
import SearchResultsPage from "./pages/SearchResultsPage";

export default function App() {
  const [user, setUser] = useState(null);

  return (
    <BrowserRouter>
      {user && <SearchBar />}
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" /> : <LoginForm onSuccess={setUser} />} />
        <Route path="/signup" element={user ? <Navigate to="/" /> : <SignupForm />} />
        <Route path="/boards/:bid" element={user ? <BoardPinsPage /> : <Navigate to="/login" />} />
        <Route path="/search" element={user ? <SearchResultsPage /> : <Navigate to="/login" />} />
        <Route path="/" element={user ? <FeedPage /> : <BoardsPage />} />
      </Routes>
    </BrowserRouter>
  );
}


