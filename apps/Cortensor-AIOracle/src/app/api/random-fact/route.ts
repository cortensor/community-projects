import { NextResponse } from 'next/server'
import { fetchRandomFact } from '@/lib/random-facts'

export async function GET() {
  try {
    const fact = await fetchRandomFact()
    if (!fact) {
      return NextResponse.json({ error: 'No fact available' }, { status: 503 })
    }

    return NextResponse.json(fact, {
      status: 200,
      headers: {
        'Cache-Control': 'no-store'
      }
    })
  } catch (err) {
    console.error('[RandomFactAPI] unexpected error', err)
    return NextResponse.json({ error: 'Failed to fetch random fact' }, { status: 500 })
  }
}
