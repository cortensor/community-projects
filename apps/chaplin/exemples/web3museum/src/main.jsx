import React from "react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import "./index.css";
import Home from "./pages/Home.jsx";



createRoot(document.getElementById("root")).render(
  <StrictMode>
    
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home/>} />
          
        </Routes>
      </BrowserRouter>
   
  </StrictMode>
);