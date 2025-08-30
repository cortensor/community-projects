import { NextRequest } from 'next/server'
import { CORTENSOR_CONFIG } from '@/lib/config'
import { getModelConfig } from '@/lib/models'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const query = searchParams.get('query') || ''
    const sessionId = searchParams.get('sessionId') || String(CORTENSOR_CONFIG.SESSION_ID)
    const modelId = searchParams.get('modelId') || 'deepseek-r1'
    const miners = Math.max(3, Math.min(parseInt(searchParams.get('miners') || '5', 10), 15))
    const temperature = parseFloat(searchParams.get('temperature') || '0.7')
    const topK = parseInt(searchParams.get('topK') || '40', 10)
    const topP = parseFloat(searchParams.get('topP') || '0.95')

    if (!query) {
      return new Response('query is required', { status: 400 })
    }

    const model = getModelConfig(modelId)
    const timeoutSec = Number.isFinite(CORTENSOR_CONFIG.TIMEOUT) && CORTENSOR_CONFIG.TIMEOUT > 0
      ? CORTENSOR_CONFIG.TIMEOUT
      : (model.timeout || 600)
    const maxTokens = Number.isFinite(CORTENSOR_CONFIG.MAX_TOKENS) && CORTENSOR_CONFIG.MAX_TOKENS > 0
      ? CORTENSOR_CONFIG.MAX_TOKENS
      : (model.maxTokens || 1024)

    const routerUrl = `${CORTENSOR_CONFIG.ROUTER_URL}/api/v1/completions/${sessionId}`
    const payload = {
      prompt: query,
      prompt_type: 1,
      client_reference: `oracle-stream-${Date.now()}`,
      stream: true,
      timeout: timeoutSec,
      max_tokens: maxTokens,
      max_miners: miners,
      temperature: Number.isFinite(temperature) ? temperature : model.temperature,
      top_p: Number.isFinite(topP) ? topP : model.topP,
      top_k: Number.isFinite(topK) ? topK : model.topK,
      presence_penalty: model.presencePenalty ?? 0,
      frequency_penalty: model.frequencyPenalty ?? 0,
    }

    const upstream = await fetch(routerUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${CORTENSOR_CONFIG.API_KEY}`,
      },
      body: JSON.stringify(payload),
      // Let router control streaming; no AbortSignal to avoid early cut
    })

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => '')
      return new Response(`router error: ${upstream.status} ${text}`, { status: 502 })
    }

    // Proxy the SSE stream to the client
    const stream = new ReadableStream({
      async start(controller) {
        const reader = upstream.body!.getReader()
        const encoder = new TextEncoder()
        // Send initial SSE headers/data to keep connection alive
        controller.enqueue(encoder.encode(': connected\n\n'))
        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            if (value) controller.enqueue(value)
          }
        } catch (e) {
          // swallow stream errors to finalize response
        } finally {
          controller.close()
        }
      }
    })

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        // CORS same-origin assumed in Next.js for API routes
      },
    })
  } catch (err: any) {
    return new Response(`stream setup failed: ${err?.message || 'unknown error'}`, { status: 500 })
  }
}
