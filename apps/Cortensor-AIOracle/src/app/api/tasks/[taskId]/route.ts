import { NextRequest, NextResponse } from 'next/server'
import { cortensorService } from '@/lib/cortensor'

export async function GET(_request: NextRequest, context: { params: { taskId: string } }) {
  try {
    const taskId = context.params.taskId
    const res = await cortensorService.getTaskById(taskId)
    if (!res.success) {
      return NextResponse.json({ error: res.error || 'Failed to fetch task' }, { status: 500 })
    }
    return NextResponse.json(res.data)
  } catch (err) {
    return NextResponse.json({ error: 'Unexpected error fetching task' }, { status: 500 })
  }
}
