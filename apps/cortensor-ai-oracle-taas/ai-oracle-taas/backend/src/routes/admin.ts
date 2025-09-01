import { Router, type Request, type Response } from "express"
import { getDatabase } from "../config/database"
import { getRedis } from "../config/redis"
import { logger } from "../utils/logger"
import { authenticateToken } from "./auth"

const router = Router()

// Admin middleware - check if user is admin
const requireAdmin = async (req: Request, res: Response, next: any) => {
  try {
    const db = getDatabase()
    const result = await db.query("SELECT role FROM users WHERE id = $1", [req.user.userId])

    if (result.rows.length === 0 || result.rows[0].role !== "admin") {
      return res.status(403).json({ error: "Admin access required" })
    }

    next()
  } catch (error) {
    logger.error("Admin check error:", error)
    res.status(500).json({ error: "Internal server error" })
  }
}

// Get system stats
router.get("/stats", authenticateToken, requireAdmin, async (req: Request, res: Response) => {
  try {
    const db = getDatabase()

    // Get user count
    const userCount = await db.query("SELECT COUNT(*) FROM users")

    // Get query count
    const queryCount = await db.query("SELECT COUNT(*) FROM queries")

    // Get queries by status
    const queryStats = await db.query(`
      SELECT status, COUNT(*) as count 
      FROM queries 
      GROUP BY status
    `)

    // Get recent activity
    const recentQueries = await db.query(`
      SELECT q.id, q.query_text, q.status, q.created_at, u.username
      FROM queries q
      JOIN users u ON q.user_id = u.id
      ORDER BY q.created_at DESC
      LIMIT 10
    `)

    res.json({
      stats: {
        totalUsers: Number(userCount.rows[0].count),
        totalQueries: Number(queryCount.rows[0].count),
        querysByStatus: queryStats.rows.reduce((acc, row) => {
          acc[row.status] = Number(row.count)
          return acc
        }, {}),
      },
      recentActivity: recentQueries.rows,
    })
  } catch (error) {
    logger.error("Error fetching admin stats:", error)
    res.status(500).json({ error: "Internal server error" })
  }
})

// Get all users
router.get("/users", authenticateToken, requireAdmin, async (req: Request, res: Response) => {
  try {
    const { page = 1, limit = 20 } = req.query
    const offset = (Number(page) - 1) * Number(limit)

    const db = getDatabase()
    const result = await db.query(
      `SELECT id, email, username, role, created_at, 
              (SELECT COUNT(*) FROM queries WHERE user_id = users.id) as query_count
       FROM users 
       ORDER BY created_at DESC 
       LIMIT $1 OFFSET $2`,
      [limit, offset],
    )

    const countResult = await db.query("SELECT COUNT(*) FROM users")

    res.json({
      users: result.rows,
      pagination: {
        page: Number(page),
        limit: Number(limit),
        total: Number(countResult.rows[0].count),
        totalPages: Math.ceil(Number(countResult.rows[0].count) / Number(limit)),
      },
    })
  } catch (error) {
    logger.error("Error fetching users:", error)
    res.status(500).json({ error: "Internal server error" })
  }
})

// Update user role
router.patch("/users/:id/role", authenticateToken, requireAdmin, async (req: Request, res: Response) => {
  try {
    const { id } = req.params
    const { role } = req.body

    const validRoles = ["user", "admin", "moderator"]
    if (!validRoles.includes(role)) {
      return res.status(400).json({ error: "Invalid role" })
    }

    const db = getDatabase()
    const result = await db.query("UPDATE users SET role = $1 WHERE id = $2 RETURNING id, email, username, role", [
      role,
      id,
    ])

    if (result.rows.length === 0) {
      return res.status(404).json({ error: "User not found" })
    }

    logger.info(`User role updated: ${id} -> ${role} by admin ${req.user.userId}`)
    res.json({
      message: "User role updated successfully",
      user: result.rows[0],
    })
  } catch (error) {
    logger.error("Error updating user role:", error)
    res.status(500).json({ error: "Internal server error" })
  }
})

// Get all queries (admin view)
router.get("/queries", authenticateToken, requireAdmin, async (req: Request, res: Response) => {
  try {
    const { page = 1, limit = 20, status, userId } = req.query
    const offset = (Number(page) - 1) * Number(limit)

    let query = `
      SELECT q.id, q.query_text, q.response, q.status, q.created_at, q.updated_at,
             u.username, u.email
      FROM queries q
      JOIN users u ON q.user_id = u.id
    `
    const params: any[] = []
    const conditions: string[] = []

    if (status) {
      conditions.push(`q.status = $${params.length + 1}`)
      params.push(status)
    }

    if (userId) {
      conditions.push(`q.user_id = $${params.length + 1}`)
      params.push(userId)
    }

    if (conditions.length > 0) {
      query += ` WHERE ${conditions.join(" AND ")}`
    }

    query += ` ORDER BY q.created_at DESC LIMIT $${params.length + 1} OFFSET $${params.length + 2}`
    params.push(limit, offset)

    const db = getDatabase()
    const result = await db.query(query, params)

    // Get total count
    let countQuery = "SELECT COUNT(*) FROM queries q"
    const countParams: any[] = []

    if (conditions.length > 0) {
      countQuery += ` WHERE ${conditions.join(" AND ")}`
      countParams.push(...params.slice(0, -2)) // Remove limit and offset
    }

    const countResult = await db.query(countQuery, countParams)

    res.json({
      queries: result.rows,
      pagination: {
        page: Number(page),
        limit: Number(limit),
        total: Number(countResult.rows[0].count),
        totalPages: Math.ceil(Number(countResult.rows[0].count) / Number(limit)),
      },
    })
  } catch (error) {
    logger.error("Error fetching admin queries:", error)
    res.status(500).json({ error: "Internal server error" })
  }
})

// Clear Redis cache
router.post("/cache/clear", authenticateToken, requireAdmin, async (req: Request, res: Response) => {
  try {
    const redis = getRedis()
    await redis.flushAll()

    logger.info(`Redis cache cleared by admin ${req.user.userId}`)
    res.json({ message: "Cache cleared successfully" })
  } catch (error) {
    logger.error("Error clearing cache:", error)
    res.status(500).json({ error: "Internal server error" })
  }
})

export default router
