// Simple utility functions without external dependencies
export function cn(...inputs: Array<string | undefined | null | false>): string {
  return inputs.filter(Boolean).join(' ')
}

export function formatConfidence(confidence: number): string {
  return `${(confidence * 100).toFixed(1)}%`
}

export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "text-green-500"
  if (confidence >= 0.6) return "text-yellow-500"
  return "text-red-500"
}

export function truncateAddress(address: string, length = 6): string {
  return `${address.slice(0, length)}...${address.slice(-4)}`
}

export function formatTimestamp(timestamp: number): string {
  return new Date(timestamp).toLocaleString()
}

// Remove chain-of-thought: drop everything inside <think>...</think> and any text before </think>
export function sanitizeModelAnswer(text: string | undefined | null): string {
  if (!text) return ''
  let out = String(text)
  // Remove explicit <think>...</think> blocks first
  try {
    out = out.replace(/<think>[\s\S]*?<\/think>/gi, '')
  } catch {}
  // If any stray closing tag remains, drop everything before the last </think>
  const closeIdx = out.toLowerCase().lastIndexOf('</think>')
  if (closeIdx !== -1) {
    out = out.slice(closeIdx + 8)
  }
  // Remove any remaining <think> or </think> tags
  out = out.replace(/<\/?think>/gi, '')
  return out.trim()
}
