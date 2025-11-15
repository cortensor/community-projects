import React from "react";
import { useAuth } from "@clerk/clerk-react";
import { Navigate } from "react-router-dom";

function PublicRoute({ children }) {
  const { isSignedIn, isLoaded } = useAuth();
  if (!isLoaded) return null;
  if (isSignedIn) return <Navigate to="/home" replace />;
  return children;
}

export default PublicRoute;