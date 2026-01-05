import { NextRequest, NextResponse } from 'next/server'
import { addOracleFact, getOracleFacts } from '@/lib/oracle-facts'

export const revalidate = 0
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limitParam = searchParams.get('limit')
    const limit = limitParam ? Math.max(1, Math.min(100, Number(limitParam))) : 20
    const facts = await getOracleFacts(limit)
    return NextResponse.json({ data: facts })
  } catch (err) {
    console.error('GET /api/oracle-facts failed', err)
    return NextResponse.json({ error: 'Failed to load oracle facts' }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { query, answer, verdict, confidence, sources, modelName, queryId } = body || {}

    if (!query || typeof query !== 'string') {
      return NextResponse.json({ error: 'query is required' }, { status: 400 })
    }
    if (!answer || typeof answer !== 'string') {
      return NextResponse.json({ error: 'answer is required' }, { status: 400 })
    }
    if (!verdict || (verdict !== 'Yes' && verdict !== 'No')) {
      return NextResponse.json({ error: 'verdict must be Yes or No' }, { status: 400 })
    }
    if (answer.toLowerCase().startsWith('error:')) {
      return NextResponse.json({ error: 'error answers are not stored' }, { status: 400 })
    }

    const record = await addOracleFact({
      query,
      answer,
      verdict,
      confidence: typeof confidence === 'number' ? confidence : undefined,
      sources: Array.isArray(sources) ? sources : undefined,
      modelName: typeof modelName === 'string' ? modelName : undefined,
      queryId: typeof queryId === 'string' ? queryId : undefined,
    })

    return NextResponse.json({ data: record }, { status: 201 })
  } catch (err) {
    console.error('POST /api/oracle-facts failed', err)
    return NextResponse.json({ error: 'Failed to save oracle fact' }, { status: 500 })
  }
}
