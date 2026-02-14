import { runAgent } from './agentEngine.js'; 

const generalAssistantConfig = {
  agentName: "💬 General Assistant",
  systemPrompt: `This is a conversation between a "User" and an "AI."
The AI ​​is an assistant named "💬 General Assistant."
The AI ​​must answer the User's questions based on the conversation history.
The AI ​​must answer concisely and to the point, and not ask follow-up questions.`
};

export function generalAssistant(prompt, sessionId, metadata, onThinking, onDone) {
  return runAgent(prompt, sessionId, generalAssistantConfig, metadata, onThinking, onDone);
}