// This directive marks the component as a Client Component.
// It's required for using React hooks like useState, useEffect, and useRef.
"use client";

import { useState, useRef, useEffect, type FC, type KeyboardEvent } from 'react';
import { buildPrompt } from '@/promptBuilders';
import { generateId } from '@/lib/utils';

// Define the shape of a message object for strict typing.
interface Message {
  text: string;
  sender: 'user' | 'ai';
}

const ChatPage: FC = () => {
  // --- State Management ---
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // --- API Configuration ---
  // ⚠️ IMPORTANT: Replace with your server details and API Key.

  // --- DOM Reference for Scrolling ---
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // --- Auto-scrolling Effect ---
  // This hook runs after every update to the 'messages' state array.
  useEffect(() => {
    if (chatContainerRef.current) {
      const { scrollHeight, clientHeight } = chatContainerRef.current;
      chatContainerRef.current.scrollTop = scrollHeight - clientHeight;
    }
  }, [messages]);

  // --- Core Message Handling Logic ---
  const handleSendMessage = async (): Promise<void> => {
    const trimmedInput = inputText.trim();
    if (!trimmedInput || isLoading) return;

    // Add the user's message to the UI and reset the input field.
    const userMessage: Message = { text: trimmedInput, sender: 'user' };
    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      // Make the fetch request to the streaming API endpoint.
      const response = await fetch('/api/conversation', {
        method: 'POST',
        // The body now includes all parameters from the cURL command's data payload
        body: JSON.stringify({
          messages: [{ id: generateId(), role: 'user', content: trimmedInput }],
          persona: "cortensor-default",
          clientReference: generateId(),
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      // Add a placeholder for the AI's response to be updated in real-time.
      setMessages(prev => [...prev, { text: '', sender: 'ai' }]);

      // Process the stream as data arrives.
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim() === '' || !line.startsWith('data: ')) continue;

          const data = line.substring(6);
          if (data.trim() === '[DONE]') continue;

          try {
            const parsedData = JSON.parse(data);
            const content: string = parsedData.choices?.[0]?.text || '';

            if (content) {
              // --- CORRECTED IMMUTABLE UPDATE ---
              setMessages(prev => {
                const lastMessage = prev[prev.length - 1];
                const updatedMessage = {
                  ...lastMessage,
                  text: lastMessage.text + content,
                };
                return [...prev.slice(0, -1), updatedMessage];
              });
            }
          } catch (e) {
            console.error('Error parsing JSON from stream:', e, data);
          }
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "An unknown error occurred.";
      setMessages(prev => [...prev, { text: `Error: ${errorMessage}`, sender: 'ai' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void handleSendMessage();
    }
  };

  // --- JSX for Rendering the UI ---
  return (
    <main className="flex h-screen w-full flex-col items-center justify-center bg-gray-100">
      <div className="flex h-[90vh] w-full max-w-3xl flex-col rounded-xl bg-white shadow-2xl">

        {/* Chat Window */}
        <div ref={chatContainerRef} className="flex-1 space-y-4 overflow-y-auto p-6">
          {messages.map((msg, index) => (
            <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-md rounded-2xl px-4 py-2 text-base lg:max-w-lg ${msg.sender === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : 'bg-gray-200 text-gray-800 rounded-bl-none'
                  } whitespace-pre-wrap`}
              >
                {msg.text === '' && msg.sender === 'ai' ? (
                  <span className="animate-pulse">...</span>
                ) : (
                  msg.text
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 bg-white p-4">
          <div className="flex items-center space-x-3">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              rows={1}
              disabled={isLoading}
              className="flex-1 resize-none text-slate-900 rounded-lg border-2 border-gray-300 p-3 focus:border-blue-500 focus:outline-none disabled:bg-gray-100"
            />
            <button
              onClick={() => { void handleSendMessage(); }}
              disabled={isLoading}
              className="rounded-lg bg-blue-600 px-5 py-3 font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-400"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </main>
  );
};

export default ChatPage;