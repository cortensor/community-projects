import { OracleQuery, MinerResponse, CortensorApiResponse } from '@/types/oracle'

class CortensorService {
  private apiKey: string
  private baseUrl: string
  private sessionId: number
  // WebSocket fields (browser-only)
  private wsUrl?: string
  private ws?: any
  private wsConnected = false
  private wsWantOpen = false
  private wsBackoffMs = 1000
  private wsListeners: Array<(data: any) => void> = []

  constructor() {
    this.apiKey = process.env.CORTENSOR_API_KEY!
    this.baseUrl = process.env.CORTENSOR_ROUTER_URL!
  const sidRaw = process.env.NEXT_PUBLIC_DEEPSEEK_SESSION_ID
  const sid = sidRaw ? parseInt(sidRaw, 10) : 0
  this.sessionId = Number.isFinite(sid) ? sid : 0
    this.wsUrl = process.env.NEXT_PUBLIC_CORTENSOR_WS_URL || 'ws://173.214.163.250:9007'

    // Default to WebSocket in browser; REST remains available as fallback
    if (typeof window !== 'undefined') {
      this.connectWebSocket()
    }
  }

  async submitQuery(query: string): Promise<CortensorApiResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/completions/${this.sessionId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: query,
          stream: false,
          timeout: 60
        })
      })

      const data = await response.json()
      
      return {
        success: response.ok,
        data,
        timestamp: Date.now()
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now()
      }
    }
  }

  async getSessionInfo(): Promise<CortensorApiResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/sessions/${this.sessionId}`, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
        }
      })

      const data = await response.json()
      
      return {
        success: response.ok,
        data,
        timestamp: Date.now()
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now()
      }
    }
  }

  async getMiners(): Promise<CortensorApiResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/miners`, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
        }
      })

      const data = await response.json()
      
      return {
        success: response.ok,
        data,
        timestamp: Date.now()
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now()
      }
    }
  }

  async getTasks(): Promise<CortensorApiResponse> {
  // REST fallback: prefer WebSocket for live updates
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/tasks/${this.sessionId}`, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
        }
      })

      const data = await response.json()
      
      return {
        success: response.ok,
        data,
        timestamp: Date.now()
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now()
      }
    }
  }

  private extractTaskIds(payload: any): number[] {
    if (!payload) return []
    const arr = Array.isArray(payload) ? payload : (Array.isArray(payload?.tasks) ? payload.tasks : [])
    const ids: number[] = []
    for (const item of arr) {
      const id = item?.task_id ?? item?.taskId ?? item?.id
      const n = typeof id === 'string' ? parseInt(id, 10) : (typeof id === 'number' ? id : NaN)
      if (Number.isFinite(n)) ids.push(n)
    }
    return ids
  }

  async getTaskById(taskId: number | string): Promise<CortensorApiResponse> {
  // REST fallback: prefer WebSocket for live updates
    try {
      const idStr = typeof taskId === 'number' ? String(taskId) : taskId
      const response = await fetch(`${this.baseUrl}/api/v1/tasks/${this.sessionId}/${idStr}`, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
        }
      })
      const data = await response.json()
      return {
        success: response.ok,
        data,
        timestamp: Date.now()
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now()
      }
    }
  }

  async getLatestTask(): Promise<CortensorApiResponse> {
    // REST fallback: prefer WebSocket for live updates
    const list = await this.getTasks()
    if (!list.success) return list
    const ids = this.extractTaskIds(list.data)
    if (!ids.length) {
      return { success: false, error: 'No tasks found for session', timestamp: Date.now() }
    }
    const latest = Math.max(...ids)
    return this.getTaskById(latest)
  }

  // --- WebSocket-first API ---
  private wsLog(...args: any[]) {
    if (process.env.ORACLE_DEBUG_LOGS === '1' || process.env.ORACLE_DEBUG_LOGS === 'true') {
      // eslint-disable-next-line no-console
      console.log('[CortensorWS]', ...args)
    }
  }

  private scheduleReconnect() {
    if (!this.wsWantOpen) return
    const delay = Math.min(this.wsBackoffMs, 15000)
    this.wsLog('reconnect in', delay, 'ms')
    setTimeout(() => {
      this.wsBackoffMs = Math.min(this.wsBackoffMs * 2, 15000)
      this.connectWebSocket()
    }, delay)
  }

  connectWebSocket() {
    if (typeof window === 'undefined') return // only in browser
    if (!this.wsUrl) return
    if (this.ws && this.wsConnected) return
    this.wsWantOpen = true
    try {
      const WS: any = (globalThis as any).WebSocket
      if (!WS) {
        this.wsLog('WebSocket API not available in this environment')
        return
      }
      const url = this.wsUrl
      this.ws = new WS(url)
      this.wsLog('connecting to', url)
      this.ws.onopen = () => {
        this.wsConnected = true
        this.wsBackoffMs = 1000
        this.wsLog('connected')
        // Optional: send an identify/subscription message if protocol requires it
        // For generic setups, we filter onMessage by sessionId
      }
      this.ws.onclose = () => {
        this.wsConnected = false
        this.wsLog('closed')
        this.scheduleReconnect()
      }
      this.ws.onerror = (err: any) => {
        this.wsLog('error', err)
        // onerror may be followed by onclose
      }
      this.ws.onmessage = (evt: MessageEvent) => {
        try {
          const data = typeof evt.data === 'string' ? JSON.parse(evt.data) : evt.data
          // Filter by session id when present
          const sid = data?.session_id ?? data?.sessionId ?? data?.session
          if (sid != null && Number(sid) !== this.sessionId) return
          // Dispatch to listeners
          for (const cb of this.wsListeners) {
            try { cb(data) } catch {}
          }
        } catch (e) {
          // Ignore non-JSON payloads
        }
      }
    } catch (e) {
      this.wsLog('connect error', e)
      this.scheduleReconnect()
    }
  }

  disconnectWebSocket() {
    this.wsWantOpen = false
    if (this.ws) {
      try { this.ws.close() } catch {}
      this.ws = undefined
    }
  }

  onTaskEvent(listener: (data: any) => void) {
    this.wsListeners.push(listener)
    return () => {
      this.wsListeners = this.wsListeners.filter(l => l !== listener)
    }
  }
}

export const cortensorService = new CortensorService()
