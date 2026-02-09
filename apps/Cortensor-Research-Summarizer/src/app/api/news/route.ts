import { NextResponse } from 'next/server';
import { fetchNews } from '@/lib/newsService';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type Category = 'general' | 'technology' | 'science' | 'random';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const category = (searchParams.get('category') as Category) || 'general';

  try {
    const items = await fetchNews(category);
    return NextResponse.json({ items, category });
  } catch (error) {
    console.error('news route error', error);
    return NextResponse.json({ items: [], category, error: 'Failed to load news' }, { status: 500 });
  }
}
