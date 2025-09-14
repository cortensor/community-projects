import { ChatSession, Message } from '@/types';
import { ErrorState } from '@/hooks/useChatCompletion';
import { generateId } from '@/lib/utils';

// Define the structure for the callbacks
interface StreamProcessorCallbacks {
  onThinking: (thinkingContent: string) => void;
  onAnswer: (answerContent: string) => void;
  onTitle: (title: string) => void;
  onHistorySummary: (summary: string) => void;
}

export type SetChatSessions = React.Dispatch<React.SetStateAction<ChatSession[]>>;

/**
 * Creates a stream processor that parses tagged content from a stream.
 * This version immediately processes content and only buffers potential tags,
 * ensuring real-time UI updates.
 */
const createStreamProcessor = ({ onThinking, onAnswer, onTitle, onHistorySummary }: StreamProcessorCallbacks) => {
  let currentState: 'IDLE' | 'THINKING' | 'ANSWER' | 'TITLE' | 'HISTORY_SUMMARY' = 'IDLE';
  let mainBuffer = '';
  let sectionContentBuffer = '';

  const processContent = (content: string) => {
    if (!content) return;
    switch (currentState) {
      case 'THINKING':
        onThinking(content);
        break;
      case 'ANSWER':
        onAnswer(content);
        break;
      case 'TITLE':
      case 'HISTORY_SUMMARY':
        sectionContentBuffer += content;
        break;
      // In IDLE state, content is ignored as it's outside any relevant tag.
    }
  };

  const processChunk = (chunk: string) => {
    mainBuffer += chunk;

    while (true) {
      const tagStartIndex = mainBuffer.indexOf('<');

      // If there's no '<' in the buffer, the whole thing is content.
      if (tagStartIndex === -1) {
        processContent(mainBuffer);
        mainBuffer = '';
        break;
      }

      // Process and display any content that came before the potential tag.
      const contentBeforeTag = mainBuffer.substring(0, tagStartIndex);
      processContent(contentBeforeTag);

      // Keep only the part of the buffer from the '<' onwards.
      mainBuffer = mainBuffer.substring(tagStartIndex);

      // Now, check if we have a complete tag in the remaining buffer.
      const tagEndIndex = mainBuffer.indexOf('>');

      // If there's no closing '>', we need to wait for more chunks.
      if (tagEndIndex === -1) {
        break;
      }

      // Check for a nested '<', like "a < b < c".
      const nextTagStartIndex = mainBuffer.indexOf('<', 1);
      if (nextTagStartIndex !== -1 && nextTagStartIndex < tagEndIndex) {
        // The first '<' was not part of a tag, treat it as content.
        processContent('<');
        mainBuffer = mainBuffer.substring(1);
        continue; // Restart the loop with the rest of the buffer.
      }

      // A legitimate tag is found. Process it.
      const tag = mainBuffer.substring(0, tagEndIndex + 1);
      const isClosing = tag.startsWith('</');
      const tagName = tag.replace(/<\/?|>/g, '');

      if (isClosing) {
        switch (tagName) {
          case 'title':
            onTitle(sectionContentBuffer);
            break;
          case 'historysummary':
            onHistorySummary(sectionContentBuffer);
            break;
        }
        sectionContentBuffer = '';
        currentState = 'IDLE';
      } else {
        switch (tagName) {
          case 'think':
          case 'thinking':
            currentState = 'THINKING';
            break;
          case 'answer':
            currentState = 'ANSWER';
            break;
          case 'title':
            currentState = 'TITLE';
            break;
          case 'historysummary':
            currentState = 'HISTORY_SUMMARY';
            break;
        }
      }

      // Remove the processed tag from the buffer.
      mainBuffer = mainBuffer.substring(tagEndIndex + 1);
    }
  };

  const finalize = () => {
    // If the stream ends, any remaining text in the buffer is treated as content.
    if (mainBuffer) {
      processContent(mainBuffer);
      mainBuffer = '';
    }
  }

  return { processChunk, finalize };
};


/**
 * A utility function that provides helpers for processing a readable stream.
 * This is not a hook and can be called from any function.
 * @param setChatSessions - The React state setter for chat sessions.
 * @returns An object containing the processStream function.
 */
export const createStreamHelpers = (setChatSessions: SetChatSessions, setError: (error: ErrorState) => void) => {

  const processStream = async (reader: ReadableStreamDefaultReader<Uint8Array>, chatIdToUse: string) => {
    const botMessageId = generateId();


    const decoder = new TextDecoder();
    let hasRenderedFirstChunk = false;

    // This function ensures isLoading is set to false only once.
    const handleFirstRender = () => {
      if (!hasRenderedFirstChunk) {
        setChatSessions(prev =>
          prev.map(s =>
            s.id === chatIdToUse
              ? { ...s, messages: [...s.messages, { id: botMessageId, role: 'assistant', content: '', isTyping: true }], isLoading: false }
              : s
          )
        );
        hasRenderedFirstChunk = true;
      }
    };

    const updateLastMessage = (updater: (msg: Message) => Message) => {
      setChatSessions(prevSessions =>
        prevSessions.map(session => {
          if (session.id !== chatIdToUse) return session;
          const updatedMessages = session.messages.map(msg => {
            if (msg.id === botMessageId) {
              return updater(msg);
            }
            return msg;
          });
          return { ...session, messages: updatedMessages };
        })
      );
    };

    const { processChunk, finalize } = createStreamProcessor({
      onThinking: (thinkingContent) => {
        handleFirstRender();
        updateLastMessage(msg => ({
          ...msg,
          isThinking: true,
          thinking: (msg.thinking || '') + thinkingContent,
        }));
      },
      onAnswer: (answerContent) => {
        handleFirstRender();
        updateLastMessage(msg => ({
          ...msg,
          isThinking: false,
          content: (msg.content || '') + answerContent,
        }));
      },
      onTitle: (title) => {
        setChatSessions(prevSessions =>
          prevSessions.map(session =>
            session.id === chatIdToUse ? { ...session, name: title.trim() } : session
          )
        );
      },
      onHistorySummary: (summary) => {
        setChatSessions(prevSessions =>
          prevSessions.map(session =>
            session.id === chatIdToUse ? { ...session, historySummary: summary.trim() } : session
          )
        );
      },
    });

    let streamLineBuffer = '';
    let isDone = false;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          finalize();
          break;
        }

        streamLineBuffer += decoder.decode(value, { stream: true });
        const lines = streamLineBuffer.split('\n');
        streamLineBuffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim() === '' || !line.startsWith('data: ')) continue;

          const data = line.substring(6);
          if (data.trim() === '[DONE]') {
            finalize();
            isDone = true;
            return;
          }

          try {
            const parsedData = JSON.parse(data);
            const textChunk = parsedData.choices?.[0]?.text || '';
            if (textChunk) {
              processChunk(textChunk);
            }
          } catch (e) {
            console.error('Error parsing JSON from stream:', e, data);
          }
        }
      }
    } finally {
      // If for some reason the stream ends before any content is rendered,
      // ensure isLoading is still turned off.
      if (!isDone) {
        setError({ chatId: chatIdToUse, message: 'Conversation ended unexpectedly. Please retry.' });
      }
      if (!hasRenderedFirstChunk) {
        setChatSessions(prev => prev.map(s => s.id === chatIdToUse ? {
          ...s,
          isLoading: false,
        } : s));
        setError({ chatId: chatIdToUse, message: 'Failed to connect to the AI. Please retry.' });
      }
    }
  };

  return { processStream };
};