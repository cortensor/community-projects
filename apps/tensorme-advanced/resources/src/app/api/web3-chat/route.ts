import { NextRequest, NextResponse } from 'next/server';
import taskService from '@/services/taskService';
import { getLatestSessionIdForWallet } from '@/services/sessionService';
import { Message } from '@/types';

export async function POST(request: NextRequest) {
  try {
    if (!taskService.isListenerActive) {
      taskService.ensureListenersReady();
      await new Promise(resolve => setTimeout(resolve, 10000));
    }

    const { messages, persona, clientReference, userId, chatId }: {
      messages: Message[],
      persona?: string,
      clientReference: string,
      userId: string,
      chatId: string
    } = await request.json();

    if (!messages?.length || !clientReference || !userId || !chatId) {
      return NextResponse.json({ error: 'Request requires `messages`, `clientReference`, `userId`, and `chatId`.' }, { status: 400 });
    }

    const session = await getLatestSessionIdForWallet();

    taskService.processChatTask(session, messages, persona, clientReference, userId, chatId);
    return NextResponse.json({ success: true });
  } catch (error: any) {
    console.error(`[API /web3-chat] A critical error occurred: ${error.message}`);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}