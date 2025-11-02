import { type WebSocketServer, WebSocket } from "ws"
import { logger } from "../utils/logger"
import { getRedis } from "../config/redis"

interface WebSocketClient extends WebSocket {
  id?: string
  userId?: string
  isAlive?: boolean
}

const clients = new Map<string, WebSocketClient>()

export const setupWebSocket = (wss: WebSocketServer): void => {
  wss.on("connection", (ws: WebSocketClient, request) => {
    const clientId = generateClientId()
    ws.id = clientId
    ws.isAlive = true
    clients.set(clientId, ws)

    logger.info(`WebSocket client connected: ${clientId}`)

    // Handle pong responses for heartbeat
    ws.on("pong", () => {
      ws.isAlive = true
    })

    // Handle incoming messages
    ws.on("message", async (data) => {
      try {
        const message = JSON.parse(data.toString())
        await handleWebSocketMessage(ws, message)
      } catch (error) {
        logger.error("Error handling WebSocket message:", error)
        ws.send(
          JSON.stringify({
            type: "error",
            message: "Invalid message format",
          }),
        )
      }
    })

    // Handle client disconnect
    ws.on("close", () => {
      clients.delete(clientId)
      logger.info(`WebSocket client disconnected: ${clientId}`)
    })

    // Send welcome message
    ws.send(
      JSON.stringify({
        type: "connection",
        message: "Connected to AI Oracle WebSocket",
        clientId,
      }),
    )
  })

  // Heartbeat to detect broken connections
  const heartbeat = setInterval(() => {
    wss.clients.forEach((ws: WebSocketClient) => {
      if (ws.isAlive === false) {
        ws.terminate()
        if (ws.id) clients.delete(ws.id)
        return
      }

      ws.isAlive = false
      ws.ping()
    })
  }, 30000)

  wss.on("close", () => {
    clearInterval(heartbeat)
  })
}

const handleWebSocketMessage = async (ws: WebSocketClient, message: any): Promise<void> => {
  switch (message.type) {
    case "subscribe":
      await handleSubscription(ws, message.channel)
      break
    case "unsubscribe":
      await handleUnsubscription(ws, message.channel)
      break
    case "ping":
      ws.send(JSON.stringify({ type: "pong", timestamp: Date.now() }))
      break
    default:
      logger.warn(`Unknown WebSocket message type: ${message.type}`)
  }
}

const handleSubscription = async (ws: WebSocketClient, channel: string): Promise<void> => {
  try {
    // Store subscription in Redis for persistence
    const redis = getRedis()
    await redis.sAdd(`ws:subscriptions:${ws.id}`, channel)

    ws.send(
      JSON.stringify({
        type: "subscribed",
        channel,
        message: `Subscribed to ${channel}`,
      }),
    )

    logger.info(`Client ${ws.id} subscribed to ${channel}`)
  } catch (error) {
    logger.error("Error handling subscription:", error)
  }
}

const handleUnsubscription = async (ws: WebSocketClient, channel: string): Promise<void> => {
  try {
    const redis = getRedis()
    await redis.sRem(`ws:subscriptions:${ws.id}`, channel)

    ws.send(
      JSON.stringify({
        type: "unsubscribed",
        channel,
        message: `Unsubscribed from ${channel}`,
      }),
    )

    logger.info(`Client ${ws.id} unsubscribed from ${channel}`)
  } catch (error) {
    logger.error("Error handling unsubscription:", error)
  }
}

export const broadcastToChannel = async (channel: string, data: any): Promise<void> => {
  try {
    const redis = getRedis()
    const message = JSON.stringify({
      type: "broadcast",
      channel,
      data,
      timestamp: Date.now(),
    })

    // Publish to Redis for multi-instance support
    await redis.publish(`channel:${channel}`, message)

    // Send to local WebSocket clients
    for (const [clientId, ws] of clients) {
      if (ws.readyState === WebSocket.OPEN) {
        const subscriptions = await redis.sMembers(`ws:subscriptions:${clientId}`)
        if (subscriptions.includes(channel)) {
          ws.send(message)
        }
      }
    }
  } catch (error) {
    logger.error("Error broadcasting to channel:", error)
  }
}

const generateClientId = (): string => {
  return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}
