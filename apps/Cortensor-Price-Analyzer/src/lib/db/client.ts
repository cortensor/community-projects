import Database from 'better-sqlite3';
import fs from 'node:fs';
import path from 'node:path';

const DEFAULT_DATA_DIR = path.join(process.cwd(), '.data');
const DEFAULT_DB_PATH = path.join(DEFAULT_DATA_DIR, 'market-snapshots.db');

function ensureDirectoryExists(dirPath: string): void {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function resolveDbPath(): string {
  const customPath = process.env.MARKET_SNAPSHOT_DB_PATH;
  if (customPath) {
    const absolute = path.isAbsolute(customPath) ? customPath : path.join(process.cwd(), customPath);
    ensureDirectoryExists(path.dirname(absolute));
    return absolute;
  }

  ensureDirectoryExists(DEFAULT_DATA_DIR);
  return DEFAULT_DB_PATH;
}

const dbPath = resolveDbPath();

const db = new Database(dbPath);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

db.exec(`
  CREATE TABLE IF NOT EXISTS market_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    provider TEXT NOT NULL,
    payload TEXT NOT NULL,
    refreshed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
  CREATE INDEX IF NOT EXISTS idx_market_snapshots_category_created_at
    ON market_snapshots (category, created_at DESC);
`);

export const snapshotDb = db;
