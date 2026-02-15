import { Router, type Request, type Response } from "express"
import { getDatabase } from "../config/database"
import { logger } from "../utils/logger"
import { authenticateToken } from "./auth"

const router = Router()

// Get all queries for a user
router.get("/", authenticateToken, async (req: Request, res: Response) => {
  try {
    const db = getDatabase()
    const { page = 1, limit = 20 } = req.query
    const offset = (Number(page) - 1) * Number(limit)

    const result = await db.query(
      `SELECT id, query_text, response, status, created_at, updated_at 
       FROM queries 
       WHERE user_id = $1 
       ORDER BY created_at DESC 
       LIMIT $2 OFFSET $3`,
      [req.user.userId, limit, offset],
    )

    const countResult = await db.query("SELECT COUNT(*) FROM queries WHERE user_id = $1", [req.user.userId])

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
    logger.error("Error fetching queries:", error)
    res.status(500).json({ error: "Internal server error" })
  }
})

// Get specific query by ID
router.get("/:id", authenticateToken, async (req: Request, res: Response) => {
  try {
    const { id } = req.params
    const db = getDatabase()

    const result = await db.query(
      `SELECT id, query_text, response, status, created_at, updated_at 
       FROM queries 
       WHERE id = $1 AND user_id = $2`,
      [id, req.user.userId],
    )

    if (result.rows.length === 0) {
      return res.status(404).json({ error: "Query not found" })
    }

    res.json({ query: result.rows[0] })
  } catch (error) {
    logger.error("Error fetching query:", error)
    res.status(500).json({ error: "Internal server error" })
  }
})

// Create new query
router.post("/", authenticateToken, async (req: Request, res: Response) => {
  try {
    const { queryText, category = "general" } = req.body

    if (!queryText) {
      return res.status(400).json({ error: "Query text is required" })
    }

    const db = getDatabase()
    const result = await db.query(
      `INSERT INTO queries (user_id, query_text, category, status, created_at, updated_at) 
       VALUES ($1, $2, $3, 'pending', NOW(), NOW()) 
       RETURNING id, query_text, category, status, created_at`,
      [req.user.userId, queryText, category],
    )

    const query = result.rows[0]
    logger.info(`New query created: ${query.id} by user ${req.user.userId}`)

    res.status(201).json({
      message: "Query created successfully",
      query,
    })
  } catch (error) {
    logger.error("Error creating query:", error)
    res.status(500).json({ error: "Internal server error" })
  }
})

// Update query status
router.patch("/:id/status", authenticateToken, async (req: Request, res: Response) => {
  try {
    const { id } = req.params
    const { status, response } = req.body

    if (!status) {
      return res.status(400).json({ error: "Status is required" })
    }

    const validStatuses = ["pending", "processing", "completed", "failed"]
    if (!validStatuses.includes(status)) {
      return res.status(400).json({ error: "Invalid status" })
    }

    const db = getDatabase()

    // Check if query exists and belongs to user
    const existingQuery = await db.query("SELECT id FROM queries WHERE id = $1 AND user_id = $2", [id, req.user.userId])

    if (existingQuery.rows.length === 0) {
      return res.status(404).json({ error: "Query not found" })
    }

    // Update query
    const result = await db.query(
      `UPDATE queries 
       SET status = $1, response = $2, updated_at = NOW() 
       WHERE id = $3 AND user_id = $4 
       RETURNING id, query_text, response, status, updated_at`,
      [status, response || null, id, req.user.userId],
    )

    res.json({
      message: "Query updated successfully",
      query: result.rows[0],
    })
  } catch (error) {
    logger.error("Error updating query:", error)
    res.status(500).json({ error: "Internal server error" })
  }
})

// Delete query
router.delete("/:id", authenticateToken, async (req: Request, res: Response) => {
  try {
    const { id } = req.params
    const db = getDatabase()

    const result = await db.query("DELETE FROM queries WHERE id = $1 AND user_id = $2 RETURNING id", [
      id,
      req.user.userId,
    ])

    if (result.rows.length === 0) {
      return res.status(404).json({ error: "Query not found" })
    }

    logger.info(`Query deleted: ${id} by user ${req.user.userId}`)
    res.json({ message: "Query deleted successfully" })
  } catch (error) {
    logger.error("Error deleting query:", error)
    res.status(500).json({ error: "Internal server error" })
  }
})

export default router
