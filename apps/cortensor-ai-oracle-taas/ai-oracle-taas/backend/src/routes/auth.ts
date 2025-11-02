import { Router, type Request, type Response } from "express"
import bcrypt from "bcrypt"
import jwt from "jsonwebtoken"
import { getDatabase } from "../config/database"
import { logger } from "../utils/logger"

const router = Router()

// Register new user
router.post("/register", async (req: Request, res: Response) => {
  try {
    const { email, password, username } = req.body

    if (!email || !password || !username) {
      return res.status(400).json({ error: "Email, password, and username are required" })
    }

    const db = getDatabase()

    // Check if user already exists
    const existingUser = await db.query("SELECT id FROM users WHERE email = $1 OR username = $2", [email, username])

    if (existingUser.rows.length > 0) {
      return res.status(409).json({ error: "User already exists" })
    }

    // Hash password
    const saltRounds = 12
    const hashedPassword = await bcrypt.hash(password, saltRounds)

    // Create user
    const result = await db.query(
      `INSERT INTO users (email, username, password_hash, created_at) 
       VALUES ($1, $2, $3, NOW()) 
       RETURNING id, email, username, created_at`,
      [email, username, hashedPassword],
    )

    const user = result.rows[0]
    logger.info(`New user registered: ${user.email}`)

    res.status(201).json({
      message: "User registered successfully",
      user: {
        id: user.id,
        email: user.email,
        username: user.username,
        createdAt: user.created_at,
      },
    })
  } catch (error) {
    logger.error("Registration error:", error)
    res.status(500).json({ error: "Internal server error" })
  }
})

// Login user
router.post("/login", async (req: Request, res: Response) => {
  try {
    const { email, password } = req.body

    if (!email || !password) {
      return res.status(400).json({ error: "Email and password are required" })
    }

    const db = getDatabase()

    // Find user
    const result = await db.query("SELECT id, email, username, password_hash, created_at FROM users WHERE email = $1", [
      email,
    ])

    if (result.rows.length === 0) {
      return res.status(401).json({ error: "Invalid credentials" })
    }

    const user = result.rows[0]

    // Verify password
    const isValidPassword = await bcrypt.compare(password, user.password_hash)
    if (!isValidPassword) {
      return res.status(401).json({ error: "Invalid credentials" })
    }

    // Generate JWT token
    const token = jwt.sign({ userId: user.id, email: user.email }, process.env.JWT_SECRET || "fallback-secret", {
      expiresIn: "24h",
    })

    logger.info(`User logged in: ${user.email}`)

    res.json({
      message: "Login successful",
      token,
      user: {
        id: user.id,
        email: user.email,
        username: user.username,
        createdAt: user.created_at,
      },
    })
  } catch (error) {
    logger.error("Login error:", error)
    res.status(500).json({ error: "Internal server error" })
  }
})

// Verify token middleware
export const authenticateToken = (req: Request, res: Response, next: any) => {
  const authHeader = req.headers["authorization"]
  const token = authHeader && authHeader.split(" ")[1]

  if (!token) {
    return res.status(401).json({ error: "Access token required" })
  }

  jwt.verify(token, process.env.JWT_SECRET || "fallback-secret", (err: any, user: any) => {
    if (err) {
      return res.status(403).json({ error: "Invalid or expired token" })
    }
    req.user = user
    next()
  })
}

// Get current user profile
router.get("/profile", authenticateToken, async (req: Request, res: Response) => {
  try {
    const db = getDatabase()
    const result = await db.query("SELECT id, email, username, created_at FROM users WHERE id = $1", [req.user.userId])

    if (result.rows.length === 0) {
      return res.status(404).json({ error: "User not found" })
    }

    res.json({ user: result.rows[0] })
  } catch (error) {
    logger.error("Profile fetch error:", error)
    res.status(500).json({ error: "Internal server error" })
  }
})

export default router
