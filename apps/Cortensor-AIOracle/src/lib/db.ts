import fs from 'fs'
import path from 'path'
import Database from 'better-sqlite3'

let db: Database.Database | null = null

function ensureDirForFile(filePath: string) {
  const dir = path.dirname(filePath)
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })
}

function getDbPath() {
  return (
    process.env.ORACLE_FACTS_DB_PATH ||
    path.join(process.cwd(), 'data', 'oracle-facts.sqlite')
  )
}

function initSchema(database: Database.Database) {
  database.pragma('journal_mode = WAL')
  database.pragma('synchronous = NORMAL')

  database.exec(`
    CREATE TABLE IF NOT EXISTS _migrations (
      key TEXT PRIMARY KEY,
      value TEXT,
      applied_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS oracle_facts (
      id TEXT PRIMARY KEY,
      query TEXT NOT NULL,
      answer TEXT NOT NULL,
      verdict TEXT NOT NULL,
      confidence REAL,
      sources_json TEXT,
      model_name TEXT,
      query_id TEXT,
      created_at TEXT NOT NULL
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_oracle_facts_query_id
      ON oracle_facts(query_id)
      WHERE query_id IS NOT NULL;

    CREATE INDEX IF NOT EXISTS idx_oracle_facts_created_at
      ON oracle_facts(created_at DESC);
  `)
}

export function getSqliteDb() {
  if (db) return db

  const dbPath = getDbPath()
  ensureDirForFile(dbPath)

  db = new Database(dbPath)
  initSchema(db)
  return db
}
