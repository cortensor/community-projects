import fs from 'fs/promises'
import path from 'path'

export type OracleFact = {
  id: string
  query: string
  answer: string
  verdict: 'Yes' | 'No'
  confidence?: number
  sources?: Array<{
    title: string
    url: string
    reliability?: string
    snippet?: string
    publishedAt?: string
    publisher?: string
  }>
  modelName?: string
  queryId?: string
  createdAt: string
}

const FACTS_PATH = path.join(process.cwd(), 'data', 'oracle-facts.json')

async function ensureStore() {
  const dir = path.dirname(FACTS_PATH)
  await fs.mkdir(dir, { recursive: true })
  try {
    await fs.access(FACTS_PATH)
  } catch {
    await fs.writeFile(FACTS_PATH, '[]', 'utf8')
  }
}

export async function getOracleFacts(limit = 20): Promise<OracleFact[]> {
  await ensureStore()
  const raw = await fs.readFile(FACTS_PATH, 'utf8')
  let parsed: OracleFact[] = []
  try {
    parsed = JSON.parse(raw)
  } catch {
    parsed = []
  }
  const sorted = parsed.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
  return sorted.slice(0, Math.max(1, limit))
}

export async function addOracleFact(fact: Omit<OracleFact, 'id' | 'createdAt'> & { id?: string; createdAt?: string }) {
  await ensureStore()
  const raw = await fs.readFile(FACTS_PATH, 'utf8')
  let parsed: OracleFact[] = []
  try {
    parsed = JSON.parse(raw)
  } catch {
    parsed = []
  }

  // Skip duplicates based on queryId when available
  if (fact.queryId) {
    const exists = parsed.some(f => f.queryId === fact.queryId)
    if (exists) return parsed.find(f => f.queryId === fact.queryId) as OracleFact
  }

  const record: OracleFact = {
    id: fact.id || `fact-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    query: fact.query,
    answer: fact.answer,
    verdict: fact.verdict,
    confidence: fact.confidence,
    sources: fact.sources?.slice(0, 5),
    modelName: fact.modelName,
    queryId: fact.queryId,
    createdAt: fact.createdAt || new Date().toISOString()
  }

  const next = [record, ...parsed]
  const capped = next.slice(0, 200)
  await fs.writeFile(FACTS_PATH, JSON.stringify(capped, null, 2), 'utf8')
  return record
}
