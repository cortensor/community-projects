import { NextResponse } from 'next/server';
import { sseManager } from '@/lib/sse';

export const dynamic = 'force-dynamic';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ userId: string }> }
) {
  const { userId } = await params;

  if (!userId) {
    return new NextResponse('User ID is required.', { status: 400 });
  }


  const stream = new ReadableStream({
    start(controller) {
      const emitter = sseManager.getEmitter(userId);
      let intervalId: NodeJS.Timeout;

      const listener = (data: { clientReference: string; status: string; taskId?: string, chatId: string }) => {
        try {
          controller.enqueue(`data: ${JSON.stringify(data)}\n\n`);
        } catch (e) {
        }
      };

      const sendHeartbeat = () => {
        try {
          controller.enqueue(`: heartbeat\n\n`);
        } catch (e) {
        }
      };

      emitter.on('statusUpdate', listener);

      sendHeartbeat();
      intervalId = setInterval(sendHeartbeat, 10000);

      request.signal.addEventListener('abort', () => {
        clearInterval(intervalId);
        sseManager.removeEmitter(userId);
      });
    },
  });

  return new NextResponse(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}