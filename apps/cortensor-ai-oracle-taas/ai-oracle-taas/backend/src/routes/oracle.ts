import express from "express"
import { body, param, validationResult } from "express-validator"
import rateLimit from "express-rate-limit"
import { v4 as uuidv4 } from "uuid"

import { cortensorService } from "../services/cortensorService"
import { consensusService } from "../services/consensusService"
import { getDatabase } from "../config/database"
import { logger } from "../utils/logger"

const router = express.Router()

// Rate limiting for oracle queries
const oracleRateLimit = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 5, // 5 queries per minute
  message: "Too many oracle queries, please try again later.",
})

// Submit new truth query
router.post(
  "/query",
  oracleRateLimit,
  [
    body("query").isString().isLength({ min: 10, max: 1000 }).trim(),
    body("queryType").isIn(["fact", "opinion", "calculation", "prediction"]),
    body("minerCount").optional().isInt({ min: 1, max: 10 }),
    body("consensusThreshold").optional().isFloat({ min: 0.5, max: 1.0 }),
    body("timeoutMs").optional().isInt({ min: 5000, max: 60000 }),
  ],
  async (req, res) => {
    try {
      const errors = validationResult(req)
      if (!errors.isEmpty()) {
        return res.status(400).json({ errors: errors.array() })
      }

      const { query, queryType, minerCount = 3, consensusThreshold = 0.8, timeoutMs = 30000 } = req.body

      const queryId = uuidv4()
      const userId = req.user?.id || null

      // Store query in database
      const db = getDatabase()
      await db.query(
        `INSERT INTO queries (id, user_id, query_text, query_type, miner_count, consensus_threshold, timeout_ms, status)
         VALUES ($1, $2, $3, $4, $5, $6, $7, 'processing')`,
        [queryId, userId, query, queryType, minerCount, consensusThreshold, timeoutMs],
      )

      // Process query asynchronously
      processOracleQuery(queryId, query, {
        minerCount,
        consensusThreshold,
        timeoutMs,
      }).catch((error) => {
        logger.error(`Failed to process query ${queryId}:`, error)
      })

      res.status(202).json({
        queryId,
        status: "processing",
        message: "Query submitted successfully. Processing with Cortensor network.",
        estimatedTime: `${Math.ceil(timeoutMs / 1000)} seconds`,
      })
    } catch (error) {
      logger.error("Oracle query submission failed:", error)
      res.status(500).json({ error: "Failed to submit query" })
    }
  },
)

// Get query result
router.get("/result/:queryId", [param("queryId").isUUID()], async (req, res) => {
  try {
    const errors = validationResult(req)
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() })
    }

    const { queryId } = req.params
    const db = getDatabase()

    // Get query details
    const queryResult = await db.query("SELECT * FROM queries WHERE id = $1", [queryId])

    if (queryResult.rows.length === 0) {
      return res.status(404).json({ error: "Query not found" })
    }

    const query = queryResult.rows[0]

    // Get truth record if completed
    let truthRecord = null
    if (query.status === "completed") {
      const truthResult = await db.query("SELECT * FROM truth_records WHERE query_id = $1", [queryId])
      truthRecord = truthResult.rows[0] || null
    }

    // Get miner responses
    const responsesResult = await db.query("SELECT * FROM miner_responses WHERE query_id = $1 ORDER BY created_at", [
      queryId,
    ])

    res.json({
      query: {
        id: query.id,
        text: query.query_text,
        type: query.query_type,
        status: query.status,
        createdAt: query.created_at,
        completedAt: query.completed_at,
      },
      truthRecord: truthRecord
        ? {
            consensusAnswer: truthRecord.consensus_answer,
            truthScore: Number.parseFloat(truthRecord.truth_score),
            consensusAlgorithm: truthRecord.consensus_algorithm,
            verificationStatus: truthRecord.verification_status,
            consensusDetails: truthRecord.consensus_details,
          }
        : null,
      minerResponses: responsesResult.rows.map((r) => ({
        minerId: r.miner_id,
        response: r.response_text,
        confidence: Number.parseFloat(r.confidence_score),
        responseTime: r.response_time_ms,
        sources: r.sources,
        createdAt: r.created_at,
      })),
    })
  } catch (error) {
    logger.error("Failed to get query result:", error)
    res.status(500).json({ error: "Failed to retrieve query result" })
  }
})

// Get query status
router.get("/status/:queryId", [param("queryId").isUUID()], async (req, res) => {
  try {
    const errors = validationResult(req)
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() })
    }

    const { queryId } = req.params
    const db = getDatabase()

    const result = await db.query("SELECT id, status, created_at, completed_at FROM queries WHERE id = $1", [queryId])

    if (result.rows.length === 0) {
      return res.status(404).json({ error: "Query not found" })
    }

    const query = result.rows[0]
    res.json({
      queryId: query.id,
      status: query.status,
      createdAt: query.created_at,
      completedAt: query.completed_at,
    })
  } catch (error) {
    logger.error("Failed to get query status:", error)
    res.status(500).json({ error: "Failed to retrieve query status" })
  }
})

// Process oracle query (internal function)
async function processOracleQuery(queryId: string, query: string, options: any): Promise<void> {
  const db = getDatabase()

  try {
    logger.info(`Processing oracle query ${queryId}: ${query}`)

    // Get available miners
    const miners = await cortensorService.getAvailableMiners()
    const selectedMiners = miners
      .sort((a, b) => b.reputation - a.reputation)
      .slice(0, options.minerCount)
      .map((m) => m.id)

    if (selectedMiners.length === 0) {
      throw new Error("No miners available")
    }

    // Query miners
    const responses = await cortensorService.queryMultipleMiners(query, selectedMiners, options)

    if (responses.length === 0) {
      throw new Error("No responses received from miners")
    }

    // Store miner responses
    for (const response of responses) {
      await db.query(
        `INSERT INTO miner_responses (query_id, miner_id, response_text, confidence_score, response_time_ms, sources)
         VALUES ($1, $2, $3, $4, $5, $6)`,
        [
          queryId,
          response.minerId,
          response.response,
          response.confidence,
          response.responseTime,
          JSON.stringify(response.sources || []),
        ],
      )
    }

    // Build consensus
    const consensus = await consensusService.buildConsensus(responses, options.consensusThreshold)

    // Store truth record
    await db.query(
      `INSERT INTO truth_records (query_id, consensus_answer, truth_score, consensus_algorithm, miner_count, verification_status, consensus_details)
       VALUES ($1, $2, $3, $4, $5, $6, $7)`,
      [
        queryId,
        consensus.consensusAnswer,
        consensus.consensusScore,
        "multi_algorithm",
        responses.length,
        consensus.consensusReached ? "verified" : "disputed",
        JSON.stringify(consensus),
      ],
    )

    // Update query status
    await db.query("UPDATE queries SET status = $1, completed_at = NOW() WHERE id = $2", ["completed", queryId])

    logger.info(`Oracle query ${queryId} completed successfully`)
  } catch (error) {
    logger.error(`Oracle query ${queryId} failed:`, error)

    // Update query status to failed
    await db.query("UPDATE queries SET status = $1, completed_at = NOW() WHERE id = $2", ["failed", queryId])
  }
}

export default router
