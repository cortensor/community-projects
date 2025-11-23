
// Allow responses up to 30 seconds
import { CHAT_HISTORY_LIMIT } from "@repo/ai/server";
import { cortiGPTAgent } from "@repo/ai/server";

// Define message type
interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

// Function to clean sources from assistant messages
function cleanSourcesFromMessage(content: string): string {
  // Remove "Search Results:" section and everything after it
  const searchResultsIndex = content.indexOf('Search Results:');
  if (searchResultsIndex !== -1) {
    return content.substring(0, searchResultsIndex).trim();
  }
  
  // Remove "Sources:" section and everything after it
  const sourcesIndex = content.indexOf('Sources:');
  if (sourcesIndex !== -1) {
    return content.substring(0, sourcesIndex).trim();
  }
  
  return content;
}

export async function POST(req: Request) {
  // Extract userAddress and chatId from search params
  const url = new URL(req.url);
  const userAddressFromParams = url.searchParams.get('userAddress');
  const chatIdFromParams = url.searchParams.get('chatId');

  // Extract the messages from the request body
  const { messages } = await req.json() as { messages: Message[] };
  console.log("this is the messages that are being sent", { messages })

  // Use userAddress and chatId from params
  const userAddress = userAddressFromParams;
  const chatId = chatIdFromParams;

  if (!userAddress) {
    return Response.json({ error: 'userAddress is required' }, { status: 400 });
  }

  if (!chatId) {
    return Response.json({ error: 'chatId is required' }, { status: 400 });
  }

  //TODO WOULD ADD PROPER AUTHENTICATION USING SIWE
  // Get the cortiGPT agent instance from Mastra

  // Extract the last user message from the messages array
  const lastMessage = messages[messages.length - 1];

  if (!lastMessage || lastMessage.role !== 'user') {
    return Response.json({ error: 'No user message found' }, { status: 400 });
  }

  // Get the last N messages for context (manual memory handling)
  const chatHistory = messages.slice(-CHAT_HISTORY_LIMIT);
  
  // Clean sources from assistant messages in chat history
  const cleanedChatHistory = chatHistory.map((msg: Message) => {
    if (msg.role === 'assistant') {
      return {
        ...msg,
        content: cleanSourcesFromMessage(msg.content)
      };
    }
    return msg;
  });
  
  console.log("this is the cleanedChatHistory",cleanedChatHistory);
  // Create context message with cleaned history and current prompt
  const contextMessages = [
    {
      role: 'system' as const,
      content: `Here is the recent chat history for context:\n${cleanedChatHistory.slice(0, -1).map((msg: Message) => `${msg.role}: ${msg.content}`).join('\n')}\n\nNow respond to the following new message:`
    },
    lastMessage
  ];

  // Generate the response using the agent with manual memory context
  const result = await cortiGPTAgent.generate(contextMessages);

  console.log("this is the result that is being returned", { result })

  // Return the result in UIMessage format that assistant-ui expects
  const response = {
    id: `msg-${Date.now()}`,
    role: 'assistant' as const,
    content: [{
      type: 'text' as const,
      text: result.text
    }]
  };

  return Response.json(response);
}