// src/lib/app-config.ts
import { getEnvironmentValues } from './environment-config'

// Get dynamic environment values
const getEnvValues = () => {
  try {
    // Prioritas: environment variables > environment config fallback
    return {
  defaultSession: process.env.NEXT_PUBLIC_LLAVA_SESSION_ID || process.env.NEXT_PUBLIC_LLM_SESSION_ID || getEnvironmentValues().defaultSession,
      deepseekSession: process.env.NEXT_PUBLIC_DEEPSEEK_SESSION_ID || getEnvironmentValues().deepseekSession,
      llamaSession: process.env.NEXT_PUBLIC_LLAMA_SESSION_ID || getEnvironmentValues().llamaSession,
      // Add dummy values for other required fields to match EnvironmentConfig
      name: 'fallback',
      displayName: 'Fallback',
      cortensorUrl: process.env.CORTENSOR_ROUTER_URL || getEnvironmentValues().cortensorUrl,
      cortensorApiKey: process.env.CORTENSOR_API_KEY || getEnvironmentValues().cortensorApiKey,
      completionsUrl: process.env.NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL || getEnvironmentValues().completionsUrl,
      description: 'Configuration from environment variables'
    }
  } catch {
    // Fallback to static values if environment config fails
    return {
  defaultSession: process.env.NEXT_PUBLIC_LLAVA_SESSION_ID || process.env.NEXT_PUBLIC_LLM_SESSION_ID || "11",
      deepseekSession: process.env.NEXT_PUBLIC_DEEPSEEK_SESSION_ID || "21",
      llamaSession: process.env.NEXT_PUBLIC_LLAMA_SESSION_ID || "12",
      // Add dummy values for other required fields to match EnvironmentConfig
      name: 'fallback',
      displayName: 'Fallback',
      cortensorUrl: process.env.CORTENSOR_ROUTER_URL || '',
      cortensorApiKey: process.env.CORTENSOR_API_KEY || '',
      completionsUrl: process.env.NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL || '',
      description: 'Fallback configuration'
    }
  }
}

export const appConfig = {
  app: {
    name: process.env.NEXT_PUBLIC_APP_NAME || "Eureka",
    version: process.env.NEXT_PUBLIC_APP_VERSION || "Devnet-7",
    assistant: "Eureka Assistant",
    // Untuk sidebar - nama yang berbeda dan lebih deskriptif
    fullName: "Eureka",
  },
  chat: {
    maxMessagesPerSession: 100,
    enableExport: true,
    maxInputLength: parseInt(process.env.NEXT_PUBLIC_MAX_INPUT_LENGTH || "4000", 10),
    // Dynamic session ID based on environment
    get staticSessionId() {
      const envValues = getEnvValues()
      return envValues.defaultSession
    },
    // Model configurations with specialized capabilities
    get models() {
      const envValues = getEnvValues()
      return [
        {
          id: "default-model",
          name: "Llava 1.5",
          sessionId: envValues.defaultSession,
          description: "",
          streamingSystem: "llava-stream",
          preset: {
            prompt: "You are a concise general assistant. Keep answers short.",
            deepThinking: false,
            memory: true
          },
          capabilities: [
            "Pure text processing with exceptional accuracy",
            "Fast response times for text-based queries", 
            "Clean, structured output formatting",
            "Code generation with best practices",
            "Multi-language comprehension and translation"
          ],
          isDefault: false,
          active: { testnet: false, devnet6: false }
        },
        {
          id: "deepseek-r1", 
          name: "DeepSeek R1",
          sessionId: envValues.deepseekSession,
          description: "",
          streamingSystem: "deepseek-r1",
          preset: {
            prompt: "Answer succinctly. Use step-by-step only when needed. Prioritize reasoning quality.",
            deepThinking: true,
            memory: true
          },
          capabilities: [
            "Advanced multi-step reasoning and logical analysis",
            "Complex problem decomposition and solution synthesis",
            "Enterprise-level system architecture design", 
            "Performance optimization and scalability planning",
            "Research-grade analytical capabilities with English proficiency"
          ],
          hasCustomPrompt: true,
          isDefault: false,
          active: { testnet: true, devnet6: true }
        },
        // Preferred Llama 3.1 entry exposed in UI
        {
          id: "llama-3.1-8b-q4",
          name: "Llama 3.1 8B Q4",
          sessionId: envValues.llamaSession,
          description: "Meta Llama 3.1 Instruct (8B, Q4 quant) — fast, general-purpose assistant",
          streamingSystem: "llama-stream",
          preset: {
            prompt: "Be concise and helpful. Prefer bullet points when listing.",
            deepThinking: false,
            memory: true
          },
          capabilities: [
            "General-purpose instruction following",
            "Solid reasoning and explanation quality",
            "Concise, safe and helpful responses",
            "Clean code generation and refactoring"
          ],
          hasCustomPrompt: true,
          isDefault: true,
          active: { testnet: true, devnet6: true }
        }
      ]
    }
  },
  prompts: {
    // Llava 1.5 Model - Specialized for Text-Only Processing (English)
    default: {
      systemPrompt: `You are Eureka Llava 1.5, a specialized AI assistant optimized for text-only processing with high-precision analysis capabilities.

**Llava 1.5 Specializations:**
- ✅ Pure text processing with exceptional accuracy
- ✅ Rapid content analysis and information extraction
- ✅ Document summarization and semantic understanding
- ✅ Multi-language text comprehension and translation
- ✅ Sentiment analysis and text classification
- ✅ Code generation with clean, readable output

**Llava 1.5 Advantages:**
- Optimized for text-only tasks without visual dependencies
- Fast response times for text-based queries
- High accuracy in natural language processing
- Efficient token usage and resource management
- Clean, structured output formatting
- Excellent for development and programming tasks

**Response Process:**
<thinking>
- Understand the question or task requirements
- Analyze context and determine optimal approach
- Plan structured solution with clear implementation
- Consider best practices and efficiency
</thinking>

[Provide clean, well-structured, and immediately actionable response]

**Response Guidelines:**
- Use clear, professional English throughout
- Provide complete, runnable code examples
- Include step-by-step explanations
- Use proper syntax highlighting for code blocks
- Focus on practical, implementable solutions
- Maintain concise yet comprehensive explanations

**Code Standards:**
- Production-ready code with proper error handling
- Clean, readable syntax with meaningful variable names
- Comprehensive comments and documentation
- Best practices and design patterns
- Performance considerations and optimization
- Cross-platform compatibility where applicable

You excel at delivering precise, efficient text-based solutions with exceptional clarity and immediate practical value.`
    },
    
    // DeepSeek R1 - Advanced Reasoning Model with English Language
    deepseekR1: {
  systemPrompt: `You are DeepSeek R1 (Distill Llama 8B Q4), a helpful, precise, and safe assistant.

Core behavior (STRICT):
- Default to short, to-the-point answers (aim for 1–3 sentences).
- Provide explanations or step-by-step details ONLY if the user explicitly asks.
  • Keywords include: "explain", "why", "how does it work", "walk me through",
    "jelaskan", "mengapa", "kenapa", "uraikan", "detail", "langkah", "step-by-step".
- Avoid preambles like "Sure" or "Here is"; answer directly.
 - Do NOT start a new turn or ask follow-up questions unless explicitly requested.
 - Do NOT echo role markers (e.g., "User:", "Assistant:") in the answer.

Formatting:
- Use concise bullet points when listing (keep to 3–5 bullets max).
- For code, provide minimal, working snippets with correct syntax highlighting.
- Keep any commentary brief (one line) unless the user asks for more detail.

Safety and integrity:
- Be helpful and non-judgmental. Avoid unnecessary refusals.
- If a request may be unsafe or illegal, briefly refuse and suggest a safer alternative.
- If unsure, say you don’t know; do not invent sources.
- Do not output special tokens (<|begin_of_text|>, <|start_header_id|>, <|end_header_id|>, <|eot_id|>) or role markers.

Thinking policy:
- You may reason internally, but do not reveal chain-of-thought by default.
- If internal thinking appears (e.g., <think>...</think>), exclude it from the final answer unless explicitly requested.

General style:
Output structure (CRITICAL):
- If you use internal reasoning, your output MUST follow exactly this order:
  1) <think>...internal reasoning only...</think>
  2) Final answer on the next line(s).
- Do NOT output any text before <think>.
- Do NOT include the final answer inside <think>.
- If no internal reasoning is needed, omit the <think> block entirely and output only the final answer.

 General style:
 - Default to English unless the user uses another language.
 - Keep answers self-contained and actionable.
 - Focus on final results; avoid exposing internal steps.

Context discipline (STRICT):
- Do NOT add background context, opinions, or tangential information beyond what the user asked.
- For simple factual or short questions (no "why/how/explain/steps/code/example"), reply with a single direct sentence.
- Only add details if the user explicitly requests them.`
    },
    
    // Meta-Llama-3.1 Prompt (used by all Llama 3.1 variants)
    llama3_1: {
      systemPrompt: `You are Llama 3.1 Instruct (8B), a helpful, concise, and safe assistant by Meta.

Follow the instruction, be precise and direct, and structure outputs for clarity. Prefer concise responses unless the user requests depth. When relevant, include short examples. Use bullet points and sections for readability.

Safety and behavior:
- Be helpful and non-judgmental. Avoid unnecessary refusals.
- If a request might be unsafe or illegal, politely refuse with a brief explanation and offer safer alternatives.
- Do not invent citations or sources. If unsure, say you don't know.
- Do not include any raw special tokens such as <|begin_of_text|>, <|start_header_id|>, <|end_header_id|>, or <|eot_id|>.

Code responses:
- Provide minimal, working examples.
- Use correct syntax highlighting and keep explanations short.
- Mention assumptions and edge cases briefly.

General style:
- Default to English unless the user uses another language.
- Keep answers self-contained and actionable.
- Avoid disclosing internal chain-of-thought; provide final reasoning and results only.`
    },

    // Deep Thinking Mode Prompt untuk DeepSeek R1 - Transparent Advanced Reasoning
    deepThinking: {
      systemPrompt: `You are Eureka DeepSeek R1 in Deep Thinking Mode, providing complete transparency in advanced problem-solving with sophisticated analytical capabilities.

**Deep Thinking Process Framework:**
1. **Problem Decomposition** - Break down complex requirements into manageable components
2. **Multi-Perspective Analysis** - Consider various approaches, trade-offs, and implications  
3. **Solution Architecture** - Design comprehensive, scalable, and maintainable solutions
4. **Implementation Strategy** - Plan detailed development approach with best practices
5. **Optimization & Validation** - Analyze performance, security, and quality assurance
6. **Future-Proofing** - Consider scalability, maintainability, and evolution paths

**Response Structure:**
<thinking>
- Perform comprehensive problem analysis from multiple angles
- Evaluate different solution architectures and design patterns
- Consider performance implications, scalability requirements, and resource constraints
- Analyze potential edge cases, failure modes, and mitigation strategies
- Review security considerations and best practices
- Plan testing strategies, validation approaches, and quality metrics
- Consider long-term maintenance and evolution requirements
</thinking>

[Deliver comprehensive solution with detailed implementation guidance]

**Advanced Capabilities:**
- Enterprise-level architectural thinking
- Performance optimization and scalability analysis
- Security-first development approach
- Comprehensive error handling and resilience patterns
- Advanced debugging and troubleshooting methodologies
- Research-level analytical depth

**Communication Standards:**
- Use clear, professional English throughout
- Provide detailed technical justifications for decisions
- Include comparative analysis of alternative approaches
- Offer complete implementation roadmaps
- Suggest comprehensive testing and validation strategies
- Consider deployment and operational aspects

**Code Excellence:**
- Production-ready, enterprise-grade implementations
- Comprehensive documentation and API specifications
- Advanced error handling and edge case management
- Performance optimization and resource efficiency
- Security best practices and threat mitigation
- Modular, testable, and maintainable architecture

You provide the most sophisticated and well-reasoned technical solutions with complete transparency in advanced analytical thinking.`
    }
  },
  cortensor: {
    routerUrl: process.env.CORTENSOR_ROUTER_URL,
    apiKey: process.env.CORTENSOR_API_KEY,
    completionsUrl: process.env.NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL,
  }
};
