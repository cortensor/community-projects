import Database from 'better-sqlite3';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const db = new Database(join(__dirname, '../../data/incidents.db'));

db.exec(`
  CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    detected_at INTEGER NOT NULL,
    resolved_at INTEGER,
    metrics TEXT NOT NULL,
    analysis TEXT,
    actions TEXT NOT NULL,
    evidence_bundle TEXT
  );

  CREATE TABLE IF NOT EXISTS metrics_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    latency REAL NOT NULL,
    error_rate REAL NOT NULL,
    validator_score REAL NOT NULL,
    uptime REAL NOT NULL,
    request_count INTEGER NOT NULL
  );

  CREATE TABLE IF NOT EXISTS cortensor_sessions (
    session_id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    incident_id TEXT
  );

  CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
  CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics_history(timestamp);
`);

export default db;
