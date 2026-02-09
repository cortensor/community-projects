import { NextRequest, NextResponse } from 'next/server';
import { clearHistory, deleteHistoryItem, listHistory, upsertHistoryItem } from '@/lib/historyDb';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function requireUserId(raw: string | null): string {
  const userId = (raw ?? '').trim();
  if (!userId) throw new Error('userId is required');
  return userId;
}

export async function GET(req: NextRequest) {
  try {
    const userId = requireUserId(req.nextUrl.searchParams.get('userId'));
    const items = listHistory(userId);
    return NextResponse.json({ items });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Bad request';
    return NextResponse.json({ error: message }, { status: 400 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const userId = requireUserId(typeof body?.userId === 'string' ? body.userId : null);

    if (body?.action === 'clear') {
      const deleted = clearHistory(userId);
      return NextResponse.json({ success: true, deleted });
    }

    const item = body?.item;
    if (!item || typeof item.url !== 'string' || typeof item.title !== 'string' || typeof item.summary !== 'string') {
      return NextResponse.json({ error: 'item is required' }, { status: 400 });
    }

    const saved = upsertHistoryItem(userId, {
      timestamp: typeof item.timestamp === 'number' ? item.timestamp : Date.now(),
      url: item.url,
      title: item.title,
      author: typeof item.author === 'string' ? item.author : undefined,
      publishDate: typeof item.publishDate === 'string' ? item.publishDate : undefined,
      summary: item.summary,
      keyPoints: Array.isArray(item.keyPoints) ? item.keyPoints : [],
      wordCount: typeof item.wordCount === 'number' ? item.wordCount : 0,
      wasEnriched: !!item.wasEnriched,
    });

    return NextResponse.json({ success: true, item: saved });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Bad request';
    return NextResponse.json({ error: message }, { status: 400 });
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const body = await req.json();
    const userId = requireUserId(typeof body?.userId === 'string' ? body.userId : null);
    const id = typeof body?.id === 'string' ? body.id : '';
    if (!id) return NextResponse.json({ error: 'id is required' }, { status: 400 });

    const ok = deleteHistoryItem(userId, id);
    return NextResponse.json({ success: ok });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Bad request';
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
