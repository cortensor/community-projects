import { BasePromptBuilder } from './BasePromptBuilder';
import { PromptContext } from '../types';

export class DeepSeekPromptBuilder extends BasePromptBuilder {
  // Define DeepSeek-specific tokens for clarity and maintainability
  private static readonly DEEPSEEK_BOS = '<｜begin of sentence｜>';
  private static readonly DEEPSEEK_EOS = '<｜end of sentence｜>';

  constructor() {
    super('deepseek-r1', true, true); // DeepSeek supports research and domains
  }

  buildPrompt(context: PromptContext): string {
    const systemContext = this.buildSystemContext(context.persona, context.domainContext);

    const responseStructureTemplate = `
Thinking:
Follow this structured reasoning process
  - **Query Analysis**:
    - **Deconstruct:** Break down the user's query into its fundamental components and implicit questions.
    - **Intent:** Identify the user's primary goal (e.g., asking for a definition, a code example, a comparison).
    - **Constraint Checklist:** Note any constraints like desired format, tone, or simplicity.
  - **Response Strategy**:
    - **Plan:** Outline the structure of the final answer (e.g., 1. Define X, 2. Provide example, 3. Discuss implications).
    - **Knowledge Retrieval:** Identify the key facts, concepts, or data points needed. State what you know and what you need to formulate.
  - **Pre-computation Critique**:
    - **Accuracy Check:** Review the planned facts. Are they accurate? Is there a risk of hallucination? How can I verify this internally?
    - **Completeness Check:** Does the plan fully address all parts of the user's query? Am I missing any nuance?
    - **Refinement:** Adjust the plan based on this critique to improve its quality and accuracy.
  - **Answer Synthesis**:
    - **Execution:** Based on the refined plan, formulate the final response. Write the content here that will be placed inside the final <answer> tag. Ensure it adheres to all formatting and persona rules.

Title:
A concise and relevant title for the answer.

Answer:
The full, detailed, and markdown-formatted answer to the user's query goes here.

History Summary:
Summarize previous queries and responses, highlighting anything relevant to the current query.`;

    const oneShotExample = `
EXAMPLE
Current User Query:
What is the capital of France?

Your Response (follow the structure below):
Thinking: The user wants to know the capital of France. I'll provide the answer and enrich it with history, culture, and geography.
Title: The Capital of France
Answer: The capital of France is Paris. It has been France's capital since the 10th century and is renowned for its art, fashion, gastronomy, and culture.
History Summary: The user asked about the capital. I provided a detailed, well-structured answer covering all relevant aspects.`;

    const historyMessages = context.messages.slice(0, -1);
    const formattedHistory = historyMessages
      .filter((msg) => !msg.isError && msg.content.trim() !== '')
      .map(msg => {
        const cleanedContent = msg.content.split('\n').map(line => line.trim()).join(' ');
        return `${msg.role === 'user' ? 'User' : 'Assistant'}: ${cleanedContent}`;
      })
      .join('\n');

    const summary = context.historySummary || formattedHistory || '(No history yet)';
    const currentUserMessage = context.messages[context.messages.length - 1];

    return `
Instructions:
You are ${systemContext}. Today is ${context.currentDate}.
You MUST follow the structured reasoning process and generate your response using the exact headings shown in the example. Do not use XML tags.

${oneShotExample}

Chat History:
${summary}

Current User Query:
${currentUserMessage.content}

Your Response (follow the structure below):
${responseStructureTemplate}
    `.trim();
  }
}