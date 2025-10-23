import { runAgent } from './agentEngine.js'; 

const textSummarizerConfig = {
  agentName: "📝 Text Summarizer",
  systemPrompt: `You are the "Text Summarizer." Users will provide a long text. Your task is to read the text and summarize it into five key points.`
};

export function textSummarizer(prompt, sessionId, metadata, onThinking, onDone) {
  return runAgent(prompt, sessionId, textSummarizerConfig, metadata, onThinking, onDone);
}