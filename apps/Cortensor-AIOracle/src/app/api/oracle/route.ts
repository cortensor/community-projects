import { NextRequest, NextResponse } from 'next/server'
import { OracleEngine } from '../../../lib/oracle-engine'

export async function POST(request: NextRequest) {
  try {
  const { query, sessionId, modelName, temperature, topK, topP, routerText } = await request.json()

    if (!query || typeof query !== 'string') {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      )
    }
    console.log('Processing Oracle query:', query)

    const engine = new OracleEngine()
    const result = await engine.run(query, {
      sessionId,
      modelId: modelName ? modelName.toLowerCase().replace(/\s+/g, '-') : undefined,
      temperature,
  topK,
  topP,
  routerText,
    })

    if (process.env.ORACLE_DEBUG_LOGS === '1' || process.env.ORACLE_DEBUG_LOGS === 'true') {
      console.log('[OracleAPI] miners:', result.minerCount, 'addresses:', (result.minerAddresses || []).join(', '))
    }

    // Align with frontend expectations (page.tsx)
    return NextResponse.json({
      answer: result.answer,
      confidence: result.confidence,
      minerCount: result.minerCount,
      sources: result.sources,
      minerAddresses: result.minerAddresses,
      miners: result.miners,
      consensus: result.consensus,
      modelName: result.modelName,
      timestamp: result.timestamp,
  claim: result.claim,
  verdict: result.verdict,
  label: result.label,
  lastChecked: result.lastChecked,
  methodology: result.methodology,
  recommendation: result.recommendation,
  confidenceExplanation: result.confidenceExplanation,
  provenance: result.provenance,
  machineReadable: result.machineReadable,
      debug: result.debug,
    })

  } catch (error) {
    console.error('Oracle API error:', error)
    return NextResponse.json(
      { error: 'Failed to process Oracle query' },
      { status: 500 }
    )
  }
}
