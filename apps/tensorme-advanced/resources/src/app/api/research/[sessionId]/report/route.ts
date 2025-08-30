import { NextRequest, NextResponse } from 'next/server';
import { researchService } from '@/services/research/ResearchService';

export async function GET(
  request: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  try {
    const sessionId = params.sessionId;

    // Get session report
    const report = researchService.getSessionReport(sessionId);

    if (!report) {
      // Check if session exists
      if (!researchService.sessionExists(sessionId)) {
        return NextResponse.json(
          { error: 'Session not found' },
          { status: 404 }
        );
      }

      // Session exists but no report yet
      return NextResponse.json(
        { error: 'Report not yet available. Session may still be in progress.' },
        { status: 202 }
      );
    }

    return NextResponse.json(report);
  } catch (error) {
    console.error('Report API error:', error);
    return NextResponse.json(
      { error: 'Failed to get session report' },
      { status: 500 }
    );
  }
}