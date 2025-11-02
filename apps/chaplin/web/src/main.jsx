import React from "react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import "./index.css";
import Login from "./pages/Login.jsx";
import Home from "./pages/Home.jsx";
import Create from "./pages/Create.jsx";
import { ClerkProvider } from "@clerk/clerk-react";
import PublicRoute from "./auth/PublicRoute.jsx";
import ProtectedRoute from "./auth/ProtectedRoute.jsx";

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!PUBLISHABLE_KEY) {
  throw new Error("Missing Publishable Key");
}




createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ClerkProvider publishableKey={PUBLISHABLE_KEY} >
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PublicRoute><Login /></PublicRoute>} />
          <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
          <Route path="/home" element={<ProtectedRoute><Home /></ProtectedRoute>} />
          <Route path="/create" element={<ProtectedRoute><Create /></ProtectedRoute>} />
        </Routes>
      </BrowserRouter>
    </ClerkProvider>
  </StrictMode>
);