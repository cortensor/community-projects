import { Router } from "express";

const router = Router();

// Placeholder auth routes. Replace with Supabase or Firebase integration.
router.get("/me", (req, res) => {
  // In a real app verify the token and return the user.
  res.status(401).json({ message: "Unauthenticated - replace with real auth" });
});

export default router;
