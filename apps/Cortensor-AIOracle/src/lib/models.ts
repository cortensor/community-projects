// Model configurations for different AI models
export interface ModelConfig {
  id: string
  name: string
  displayName: string
  sessionId: string
  promptType: number
  nodeType: number
  maxTokens: number
  temperature: number
  topP: number
  topK: number
  presencePenalty: number
  frequencyPenalty: number
  timeout: number
  description: string
  capabilities: string[]
}

export const AVAILABLE_MODELS: ModelConfig[] = [
  {
    id: 'deepseek-r1',
    name: 'Deepseek R1',
    displayName: 'Deepseek R1',
  sessionId: process.env.NEXT_PUBLIC_DEEPSEEK_SESSION_ID || '0',
    promptType: 1, // RAW mode
    nodeType: 2, // Node type for Deepseek
    maxTokens: 5000,
    temperature: 0.7,
    topP: 0.95,
    topK: 40,
    presencePenalty: 0,
    frequencyPenalty: 0,
    timeout: 600, // 10 minutes for more miner participation
    description: 'Advanced reasoning model with step-by-step thinking',
    capabilities: ['Deep Reasoning', 'Chain of Thought', 'Technical Analysis']
  }
  // Llava 1.5 disabled for now
  // {
  //   id: 'llava-1.5',
  //   name: 'Llava 1.5',
  //   displayName: 'Llava 1.5 (Text Only)',
  //   sessionId: '9',
  //   promptType: 1, // RAW mode
  //   nodeType: 0, // Node type for Llava 1.5
  //   maxTokens: 5000,
  //   temperature: 0.7,
  //   topP: 0.95,
  //   topK: 40,
  //   presencePenalty: 0,
  //   frequencyPenalty: 0,
  //   timeout: 600, // 10 minutes for more miner participation
  //   description: 'Multimodal AI specialized in text analysis and reasoning',
  //   capabilities: ['Text Analysis', 'Factual Reasoning', 'Multi-language']
  // }
]

export function getModelConfig(modelId: string): ModelConfig {
  return AVAILABLE_MODELS.find(model => model.id === modelId) || AVAILABLE_MODELS[0]
}

export function generatePromptForModel(modelId: string, query: string, externalData?: string): string {
  const currentDate = new Date()
  const currentDateString = currentDate.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
  const currentYear = currentDate.getFullYear()

  // Enhanced context for sports/F1 queries
  let additionalContext = ''
  const queryLower = query.toLowerCase()
  if (queryLower.includes('formula 1') || queryLower.includes('f1') || 
      (queryLower.includes('race') && (queryLower.includes('won') || queryLower.includes('winner')))) {
    additionalContext = `

IMPORTANT F1 CONTEXT (Current as of ${currentDateString}):
- The 2025 Formula 1 season is ongoing
- Recent major races include Hungarian GP (August 10, 2025), Belgian GP (July 27, 2025)
- Current competitive drivers include Lando Norris (McLaren), Max Verstappen (Red Bull), Lewis Hamilton (Mercedes)
- When asked about "latest" F1 race, refer to the most recent completed race before ${currentDateString}
- Be specific about race dates and accurate about winner information
- Verify information is current for 2025 season`
  }

  // Add external data if available
  if (externalData && externalData.trim()) {
    additionalContext += `

REAL-TIME DATA SOURCES:${externalData}`
  }

  const baseContext = `CURRENT DATE: ${currentDateString} (${currentYear})${additionalContext}

ORACLE QUERY PROCESSING:
Query: "${query}"`

  switch (modelId) {
    case 'llava-1.5':
      return `${baseContext}

INSTRUCTIONS FOR LLAVA 1.5 (TEXT-ONLY MODE):
- Provide factual, comprehensive answers based on text analysis
- Focus on accuracy and evidence-based reasoning
- PRIORITIZE REAL-TIME DATA SOURCES provided above when available
- For recent events, use real-time data over training data
- If asking about "latest" events, use provided current data first
- Be specific about dates and timeframes from external sources
- If information may be outdated, clearly state this
- Use reliable sources and data, especially real-time feeds
- Keep response focused and informative
- Avoid speculation, stick to verifiable facts

RESPONSE FORMAT: Provide a clear, direct answer to the query with factual backing.`

    case 'deepseek-r1':
      return `${baseContext}

INSTRUCTIONS FOR DEEPSEEK R1 (RAW, HIGH-ACCURACY):
- Think step-by-step internally, but NEVER reveal chain-of-thought. Output only final conclusions.
- Use the REAL-TIME DATA SOURCES above when present; they override stale training data.
- Be specific with dates, numbers, symbols (USD $), and named entities.
- Prefer credible domains for claims (gov/edu, NASA, Reuters/AP, major newspapers, established fact-checkers).

STRICT OUTPUT RULES:
1) Start with a direct answer in one short sentence (no preamble). If the query is a claim/hoax check, begin with “Yes,” or “No,” clearly.
2) Then provide 2–4 bullet points of key evidence with concrete facts (dates, figures, quotes), prioritized from the provided real-time sources.
3) Then list 1–3 Sources as title + URL. Use reputable links only; avoid blogs or forums unless the claim pertains specifically to them.
4) Do NOT include chain-of-thought, internal notes, or XML-like tags (no <think>, no analysis sections).
5) Keep total output under ~180 words unless explicitly asked for more detail.

DOMAIN-SPECIFIC GUIDANCE:
- Fact-check/Hoax: If no reputable source confirms the claim, answer “No,” and cite credible debunks (e.g., NASA/.gov, Reuters/AP, Snopes/PolitiFact/FactCheck.org/FullFact). Avoid hedging if evidence is clear.
- Numeric range (e.g., prices): Provide a range “between $X and $Y” in USD, both ends numeric with thousands separators (e.g., $120,000 and $130,000). Don’t output a single point unless asked.
- Sports/F1: Prefer official sources and the latest verified results. Be precise about event name and date.
- Markets: Prefer current price/market data when provided. Avoid predictions without a justified range and evidence.

RESPONSE FORMAT TEMPLATE:
Answer: <one-sentence conclusion>
Key Evidence:
- <fact 1>
- <fact 2>
- <fact 3>
Sources:
- <title 1> — <url>
- <title 2> — <url>

Do not include any other sections.`

    default:
      return `${baseContext}

INSTRUCTIONS FOR AI ORACLE:
- Provide factual, accurate information
- PRIORITIZE REAL-TIME DATA SOURCES provided above when available
- For recent events, use current external data over training data
- If asking about "latest" events, provide most current data available
- Be specific about dates and timeframes from real-time sources
- If information may be outdated, clearly state this
- Use reliable sources and data, especially live feeds
- Keep response focused and informative

RESPONSE FORMAT: Provide a clear, direct answer to the query, citing real-time data when used.`
  }
}
