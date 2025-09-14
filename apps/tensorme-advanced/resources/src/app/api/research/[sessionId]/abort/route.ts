import { NextRequest, NextResponse } from 'next/server';
import { researchService } from '@/services/research/ResearchService';

export async function POST(
  request: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  try {
    const sessionId = params.sessionId;

    // Check if session exists
    if (!researchService.sessionExists(sessionId)) {
      return NextResponse.json(
        { error: 'Session not found' },
        { status: 404 }
      );
    }

    // Abort the session
    const success = await researchService.abortSession(sessionId);

    if (!success) {
      return NextResponse.json(
        { error: 'Failed to abort session' },
        { status: 500 }
      );
    }

    return NextResponse.json({ 
      success: true,
      message: 'Research session aborted successfully'
    });
  } catch (error) {
    console.error('Abort API error:', error);
    return NextResponse.json(
      { error: 'Failed to abort session' },
      { status: 500 }
    );
  }
}