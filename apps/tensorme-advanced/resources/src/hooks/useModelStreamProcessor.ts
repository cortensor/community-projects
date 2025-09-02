import { useCallback } from 'react';
import { ChatSession } from '@/types';
import { generateId } from '@/lib/utils';
import { getClientPromptService } from '@/promptService/client';
import { ErrorState } from './useChatCompletion';
import { useAppDispatch } from './redux';
import { addMessage, updateMessage, updateSession, endStream } from '@/store/slices/chatSlice';

export const useModelStreamProcessor = (
  setError?: React.Dispatch<React.SetStateAction<ErrorState | null>>,
  selectedModelId?: string
) => {
  const dispatch = useAppDispatch();
  const processStream = useCallback(async (
    reader: ReadableStreamDefaultReader<Uint8Array>,
    chatIdToUse: string
  ) => {
    const decoder = new TextDecoder('utf-8');
    const promptService = getClientPromptService(selectedModelId || 'deepseek-r1');
    const botMessageId = generateId();

    // Add initial bot message
    const initialBotMessage = { 
      id: botMessageId, 
      role: 'assistant' as const, 
      content: '', 
      isTyping: true 
    };
    
    // Use Redux
    dispatch(addMessage({ sessionId: chatIdToUse, message: initialBotMessage }));
    dispatch(updateSession({ sessionId: chatIdToUse, updates: { isLoading: false } }));

    let streamBuffer = '';
    let allBuffer = '';

    const processContentChunk = (textChunk: string, isComplete = false) => {
      allBuffer += textChunk;

      // Use the model-specific parsing logic on accumulated buffer
      const parsedChunk = promptService.parseStreamChunk({
        choices: [{ text: allBuffer, finish_reason: isComplete ? 'stop' : null }]
      });
      console.log('parsedChunk', parsedChunk);

      if (!parsedChunk) return;

      // Update chat title if available and changed
      if (parsedChunk.title) {
        const newTitle = parsedChunk.title.trim();
        dispatch(updateSession({ sessionId: chatIdToUse, updates: { name: newTitle } }));
      }

      // Update message content based on parsed data
      dispatch(updateMessage({
        sessionId: chatIdToUse,
        messageId: botMessageId,
        updates: {
          content: parsedChunk.content || '',
          thinking: parsedChunk.thinking || '',
          isThinking: parsedChunk.isThinking || false
        }
      }));

      // Update history summary if available and changed
      if (parsedChunk.historySummary) {
        const newSummary = parsedChunk.historySummary.trim();
        dispatch(updateSession({ sessionId: chatIdToUse, updates: { historySummary: newSummary } }));
      }
    };

    let allStreamBuffer = '';
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        streamBuffer += decoder.decode(value, { stream: true });
        allStreamBuffer += streamBuffer;
        const lines = streamBuffer.split('\n');
        streamBuffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim() === '' || !line.startsWith('data: ')) continue;
          const data = line.substring(6);
          if (data.trim() === '[DONE]') continue;

          try {
            const parsedData = JSON.parse(data);
            const textChunk = parsedData.choices?.[0]?.text || '';
            const isComplete = parsedData.choices?.[0]?.finish_reason === 'stop';
            if (textChunk) {
              processContentChunk(textChunk, isComplete);
            }
          } catch (e) {
            console.error('Error parsing JSON from stream:', e, data);
          }
        }
      }

      if (allStreamBuffer.trim() === '') {
        throw new Error('Empty response received, please retry.');
      }
    } catch (error) {
      console.error('Stream processing error:', error);
      throw error;
    }
  }, [setError, selectedModelId, dispatch]);

  return { processStream };
};