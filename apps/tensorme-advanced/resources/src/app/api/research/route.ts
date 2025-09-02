import { NextRequest, NextResponse } from 'next/server';
import { researchService } from '@/services/research/ResearchService';
import { ResearchOptions } from '@/types/research';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { query, mode, options } = body;

    if (!query || typeof query !== 'string') {
      return NextResponse.json(
        { error: 'Query is required and must be a string' },
        { status: 400 }
      );
    }

    // Prepare research options
    const researchOptions: ResearchOptions = {
      mode: mode || 'standard',
      ...options
    };

    // Start research
    const result = await researchService.startResearch(query, researchOptions);

    return NextResponse.json(result);
  } catch (error) {
    console.error('Research API error:', error);
    return NextResponse.json(
      { error: 'Failed to start research session' },
      { status: 500 }
    );
  }
}