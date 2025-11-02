// prompts/generateImagePrompt.js
export default function buildGenerateImagePrompt({ name, description, category, workgroup }) {
  // Nota: O contexto da equipe é removido porque a análise de coesão é muito complexa para um modelo mais simples.
  return `
System: You are an AI that creates prompts for image generators. Your task is to create ONE SINGLE image prompt as a string.

RULES:
1. Read the Agent Name, Category, and Description below.
2. Think of a symbolic image that represents the agent's function. Do not be literal.
3. Combine these ideas into a single descriptive sentence using keywords.
4. The prompt must be a descriptive sentence, NOT a list of items with '+' or brackets.
5. Output ONLY the final prompt string, with no other text.

---
EXAMPLE:
- Context:
  - Name: Text Revisor
  - Category: Productivity
  - Description: An agent that corrects grammar and improves writing.
- Correct Output:
  A glowing magical quill floating over an ancient scroll, correcting faded text with radiant ink, digital art, fantasy, cinematic lighting.
---

CONTEXT TO USE:
Agent Name: ${name}
Agent Category: ${category}
Agent Description: ${description}

---
Now, generate the image prompt.
`;
}