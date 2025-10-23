import { runAgent } from "./agentEngine.js"; 

const formatConverterConfig = {
  agentName: "🔄 Format Converter",
  systemPrompt: `You are the "Format Converter." Users will provide the raw data and the desired format (such as "to json," "to csv," or "to html").
Your job is to read the data and convert it to the requested format.

[VERY IMPORTANT RULE]
DO NOT add any words, explanations, or dialogue.
Your output must ONLY contain formatted text.`,
};

export function formatConverter(
  prompt,
  sessionId,
  metadata,
  onThinking,
  onDone
) {

  return runAgent(
    prompt,
    sessionId,
    formatConverterConfig,
    metadata, 
    onThinking,
    onDone
  );
}