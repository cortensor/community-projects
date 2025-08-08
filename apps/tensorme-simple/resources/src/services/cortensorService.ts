import {
  TextCompletionResponse,
  Message
} from '@/types';

export const fetchCompletion = async (
  messages: Message[],
  persona: string | undefined
): Promise<TextCompletionResponse> => {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ messages, persona }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Unknown API error.' }));
    throw new Error(errorData.message || `API Error: ${response.status}`);
  }

  return response.json() as Promise<TextCompletionResponse>;
};


export const fetchWeb3Completion = async (
  messages: Message[],
  persona: string | undefined,
  chatId: string,
  clientReference: string,
  userId: string
): Promise<TextCompletionResponse> => {
  const response = await fetch('/api/web3-chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ messages, persona, chatId, clientReference, userId }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Unknown API error from Web3 endpoint.' }));
    throw new Error(errorData.message || `API Error: ${response.status}`);
  }

  return response.json() as Promise<TextCompletionResponse>;
};