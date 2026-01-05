import fs from 'fs/promises'
import path from 'path'
import { getSqliteDb } from '@/lib/db'

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
    domain?: string
    snippet?: string
    publishedAt?: string
    publisher?: string
  }>
  modelName?: string
  queryId?: string
  createdAt: string
}

const FACTS_JSON_PATH = path.join(process.cwd(), 'data', 'oracle-facts.json')
const MIGRATION_KEY = 'oracle-facts-json-v1'

let migrateOnce: Promise<void> | null = null

function safeJsonParse<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

async function ensureMigrated() {
  if (migrateOnce) return migrateOnce
  migrateOnce = (async () => {
    const db = getSqliteDb()

    const already = db.prepare('SELECT 1 FROM _migrations WHERE key = ?').get(MIGRATION_KEY)
    if (already) return

    let jsonRaw: string | null = null
    try {
      jsonRaw = await fs.readFile(FACTS_JSON_PATH, 'utf8')
    } catch {
      // JSON file doesn't exist; mark migration as applied so we don't re-check every request
      db.prepare('INSERT OR REPLACE INTO _migrations(key, value, applied_at) VALUES(?, ?, ?)')
        .run(MIGRATION_KEY, JSON.stringify({ imported: 0, reason: 'no-json-file' }), new Date().toISOString())
      return
    }

    const parsed = safeJsonParse<OracleFact[]>(jsonRaw)
    const facts = Array.isArray(parsed) ? parsed : []
    if (facts.length === 0) {
      db.prepare('INSERT OR REPLACE INTO _migrations(key, value, applied_at) VALUES(?, ?, ?)')
        .run(MIGRATION_KEY, JSON.stringify({ imported: 0, reason: 'empty-or-invalid-json' }), new Date().toISOString())
      return
    }

    const insert = db.prepare(`
      INSERT OR IGNORE INTO oracle_facts(
        id, query, answer, verdict, confidence, sources_json, model_name, query_id, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `)

    const tx = db.transaction((rows: OracleFact[]) => {
      let imported = 0
      for (const f of rows) {
        if (!f || typeof f !== 'object') continue
        if (!f.id || !f.query || !f.answer || !f.verdict || !f.createdAt) continue
        const verdict = f.verdict === 'Yes' ? 'Yes' : f.verdict === 'No' ? 'No' : null
        if (!verdict) continue

        const sources = Array.isArray(f.sources) ? f.sources.slice(0, 5) : undefined
        const sourcesJson = sources ? JSON.stringify(sources) : null
        const confidence = typeof f.confidence === 'number' ? f.confidence : null
        const modelName = typeof f.modelName === 'string' ? f.modelName : null
        const queryId = typeof f.queryId === 'string' ? f.queryId : null
        const createdAt = typeof f.createdAt === 'string' ? f.createdAt : new Date().toISOString()

        const info = insert.run(
          String(f.id),
          String(f.query),
          String(f.answer),
          verdict,
          confidence,
          sourcesJson,
          modelName,
          queryId,
          createdAt
        )
        if (info.changes > 0) imported += 1
      }

      // Keep a hard cap similar to the old JSON store
      db.exec(`
        DELETE FROM oracle_facts
        WHERE id NOT IN (
          SELECT id FROM oracle_facts
          ORDER BY created_at DESC
          LIMIT 200
        );
      `)

      return imported
    })

    const imported = tx(facts)
    db.prepare('INSERT OR REPLACE INTO _migrations(key, value, applied_at) VALUES(?, ?, ?)')
      .run(MIGRATION_KEY, JSON.stringify({ imported, from: 'data/oracle-facts.json' }), new Date().toISOString())
  })()
  return migrateOnce
}

function rowToFact(row: any): OracleFact {
  const sources = row?.sources_json ? safeJsonParse<OracleFact['sources']>(row.sources_json) : null
  return {
    id: String(row.id),
    query: String(row.query),
    answer: String(row.answer),
    verdict: row.verdict === 'Yes' ? 'Yes' : 'No',
    confidence: typeof row.confidence === 'number' ? row.confidence : undefined,
    sources: Array.isArray(sources) ? sources : undefined,
    modelName: row.model_name != null ? String(row.model_name) : undefined,
    queryId: row.query_id != null ? String(row.query_id) : undefined,
    createdAt: String(row.created_at),
  }
}

export async function getOracleFacts(limit = 20): Promise<OracleFact[]> {
  await ensureMigrated()
  const db = getSqliteDb()
  const safeLimit = Math.max(1, Math.min(100, Math.floor(limit)))

  const rows = db
    .prepare(`
      SELECT id, query, answer, verdict, confidence, sources_json, model_name, query_id, created_at
      FROM oracle_facts
      ORDER BY created_at DESC
      LIMIT ?
    `)
    .all(safeLimit)

  return rows.map(rowToFact)
}

export async function addOracleFact(fact: Omit<OracleFact, 'id' | 'createdAt'> & { id?: string; createdAt?: string }) {
  await ensureMigrated()
  const db = getSqliteDb()

  // Skip duplicates based on queryId when available
  if (fact.queryId) {
    const existing = db
      .prepare(`
        SELECT id, query, answer, verdict, confidence, sources_json, model_name, query_id, created_at
        FROM oracle_facts
        WHERE query_id = ?
        LIMIT 1
      `)
      .get(fact.queryId)
    if (existing) return rowToFact(existing)
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

  const insert = db.prepare(`
    INSERT OR IGNORE INTO oracle_facts(
      id, query, answer, verdict, confidence, sources_json, model_name, query_id, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `)

  insert.run(
    record.id,
    record.query,
    record.answer,
    record.verdict,
    typeof record.confidence === 'number' ? record.confidence : null,
    record.sources ? JSON.stringify(record.sources) : null,
    record.modelName || null,
    record.queryId || null,
    record.createdAt
  )

  // Keep a hard cap similar to the old JSON store
  db.exec(`
    DELETE FROM oracle_facts
    WHERE id NOT IN (
      SELECT id FROM oracle_facts
      ORDER BY created_at DESC
      LIMIT 200
    );
  `)

  return record
}
