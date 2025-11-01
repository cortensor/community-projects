import { NextRequest, NextResponse } from 'next/server'
import { cortensorService } from '@/lib/cortensor'

export async function GET(_request: NextRequest) {
  try {
    const res = await cortensorService.getLatestTask()
    if (!res.success) {
      return NextResponse.json({ error: res.error || 'Failed to fetch latest task' }, { status: 500 })
    }
    return NextResponse.json(res.data)
  } catch (err) {
    return NextResponse.json({ error: 'Unexpected error fetching latest task' }, { status: 500 })
  }
}
