import { NextRequest, NextResponse } from 'next/server';
import { researchService } from '@/services/research/ResearchService';

export async function GET(
  request: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  try {
    const sessionId = params.sessionId;

    // Get session status
    const session = researchService.getSessionStatus(sessionId);

    if (!session) {
      return NextResponse.json(
        { error: 'Session not found' },
        { status: 404 }
      );
    }

    // Prepare response
    const response = {
      status: session.status,
      query: session.query,
      progress: calculateProgress(session),
      agentStates: Array.from(session.agents.values()),
      findingsCount: session.findings.length,
      startTime: session.startTime,
      endTime: session.endTime,
      errors: session.errors.map(e => e.message)
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error('Status API error:', error);
    return NextResponse.json(
      { error: 'Failed to get session status' },
      { status: 500 }
    );
  }
}

function calculateProgress(session: any): number {
  if (session.status === 'completed') return 100;
  if (session.status === 'failed' || session.status === 'aborted') return 0;
  
  // Calculate based on agent progress
  const agents = Array.from(session.agents.values());
  if (agents.length === 0) return 0;
  
  const totalProgress = agents.reduce((sum: number, agent: any) => sum + agent.progress, 0);
  return Math.round(totalProgress / agents.length);
}