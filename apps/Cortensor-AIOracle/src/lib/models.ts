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
    id: 'gpt-oss-20b',
    name: 'GPT OSS 20B',
    displayName: 'GPT OSS 20B',
    sessionId: process.env.NEXT_PUBLIC_OSS20B_SESSION_ID || process.env.NEXT_PUBLIC_DEEPSEEK_SESSION_ID || '5',
    promptType: 1, // RAW mode
    nodeType: 2,
    maxTokens: 6000,
    temperature: 0.55,
    topP: 0.9,
    topK: 40,
    presencePenalty: 0,
    frequencyPenalty: 0,
    timeout: 480, // prioritize faster turn-around for 20B
    description: 'Open-weight GPT OSS 20B tuned for factual, source-grounded answers',
    capabilities: ['Evidence-first', 'Concise Synthesis', 'Low Hallucination']
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

    case 'gpt-oss-20b':
      return `${baseContext}

INSTRUCTIONS FOR GPT OSS 20B (FACT-OPTIMIZED):
- Reason silently; never expose chain-of-thought or XML tags.
- Lead with a single-sentence answer. For claim checks, start with “Yes,” or “No,” decisively.
- Treat REAL-TIME DATA SOURCES as the primary truth; only use training data to fill small gaps.
- Use explicit numbers, dates, and currency markers (USD $). Avoid vague terms like “recently” or “about”.
- Keep total output under ~170 words unless the user asks for more.
- If uncertain, say what is missing and what would verify it.

RESPONSE FORMAT (STRICT):
Answer: <concise conclusion>
Key Evidence:
- <dated fact with number or quote>
- <another fact; prefer external data>
- <optional third fact>
Sources:
- <title> — <url>
- <title> — <url>

DOMAIN NOTES:
- Fact/Hoax: If no reputable confirmation, answer “No,” and cite high-credibility debunks (gov/edu, Reuters/AP, Snopes/PolitiFact/FactCheck/FullFact).
- Numeric ranges: give bounded ranges (e.g., between $120,000 and $130,000) instead of point estimates unless the user asks for a single value.
- Sports/F1: name the event and date; prefer official series sites or federation releases.
- Markets: prefer current price feeds; do not predict without evidence.`

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
