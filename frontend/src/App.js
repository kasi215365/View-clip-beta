import React, { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import Landing from "@/pages/Landing";
import Auth from "@/pages/Auth";
import Browse from "@/pages/Browse";
import Watch from "@/pages/Watch";
import LiveStreams from "@/pages/LiveStreams";
import StreamView from "@/pages/StreamView";
import StreamerDashboard from "@/pages/StreamerDashboard";
import AdminDashboard from "@/pages/AdminDashboard";
import Profile from "@/pages/Profile";
import { Toaster } from "@/components/ui/sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const AuthContext = React.createContext();

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('token');
      delete axios.defaults.headers.common['Authorization'];
    } finally {
      setLoading(false);
    }
  };

  const login = (token, userData) => {
    localStorage.setItem('token', token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#0A0E27]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-400"></div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, fetchUser }}>
      <div className="App">
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/auth" element={user ? <Navigate to="/browse" /> : <Auth />} />
            <Route path="/browse" element={user ? <Browse /> : <Navigate to="/auth" />} />
            <Route path="/watch/:id" element={user ? <Watch /> : <Navigate to="/auth" />} />
            <Route path="/live" element={user ? <LiveStreams /> : <Navigate to="/auth" />} />
            <Route path="/stream/:id" element={user ? <StreamView /> : <Navigate to="/auth" />} />
            <Route path="/streamer" element={user && (user.role === 'streamer' || user.role === 'admin') ? <StreamerDashboard /> : <Navigate to="/browse" />} />
            <Route path="/admin" element={user && user.role === 'admin' ? <AdminDashboard /> : <Navigate to="/browse" />} />
            <Route path="/profile" element={user ? <Profile /> : <Navigate to="/auth" />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" />
      </div>
    </AuthContext.Provider>
  );
}

export default App;
