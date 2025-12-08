import { NextResponse } from 'next/server';

export async function POST() {
  return NextResponse.json(
    {
      success: false,
      error: 'Summarization endpoint is currently disabled.',
    },
    { status: 501 },
  );
}
