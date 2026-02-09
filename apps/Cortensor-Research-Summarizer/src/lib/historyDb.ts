import 'server-only';

import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';

export interface PersistedHistoryItem {
  id: string;
  timestamp: number;
  url: string;
  title: string;
  author?: string;
  publishDate?: string;
  summary: string;
  keyPoints: string[];
  wordCount: number;
  wasEnriched: boolean;
  previewText: string;
}

function ensureDataDir(dirPath: string) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function getDbPath(): string {
  const dataDir = path.join(process.cwd(), '.data');
  ensureDataDir(dataDir);
  return path.join(dataDir, 'history.sqlite');
}

let dbSingleton: Database.Database | null = null;

function getDb(): Database.Database {
  if (dbSingleton) return dbSingleton;

  const dbPath = getDbPath();
  const db = new Database(dbPath);
  db.pragma('journal_mode = WAL');

  db.exec(`
    CREATE TABLE IF NOT EXISTS history (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      timestamp INTEGER NOT NULL,
      url TEXT NOT NULL,
      title TEXT NOT NULL,
      author TEXT,
      publish_date TEXT,
      summary TEXT NOT NULL,
      key_points_json TEXT NOT NULL,
      word_count INTEGER NOT NULL,
      was_enriched INTEGER NOT NULL,
      preview_text TEXT NOT NULL
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_history_user_url
      ON history(user_id, url);

    CREATE INDEX IF NOT EXISTS idx_history_user_timestamp
      ON history(user_id, timestamp DESC);
  `);

  dbSingleton = db;
  return db;
}

function sha256(input: string): string {
  return crypto.createHash('sha256').update(input).digest('hex');
}

function computeId(userId: string, url: string, timestamp: number): string {
  // Stable-ish per URL to support upsert; still changes if timestamp changes.
  // The unique index on (user_id, url) is the real upsert key.
  return `${userId}_${sha256(url)}_${timestamp}`;
}

export function createPreview(summary: string): string {
  const cleaned = (summary || '').replace(/\s+/g, ' ').trim();
  return cleaned.length <= 150 ? cleaned : `${cleaned.slice(0, 150)}…`;
}

export function upsertHistoryItem(userId: string, item: Omit<PersistedHistoryItem, 'id' | 'previewText'>): PersistedHistoryItem {
  const db = getDb();
  const timestamp = item.timestamp ?? Date.now();
  const id = computeId(userId, item.url, timestamp);
  const previewText = createPreview(item.summary);

  const stmt = db.prepare(`
    INSERT INTO history (
      id, user_id, timestamp, url, title, author, publish_date,
      summary, key_points_json, word_count, was_enriched, preview_text
    ) VALUES (
      @id, @user_id, @timestamp, @url, @title, @author, @publish_date,
      @summary, @key_points_json, @word_count, @was_enriched, @preview_text
    )
    ON CONFLICT(user_id, url) DO UPDATE SET
      id = excluded.id,
      timestamp = excluded.timestamp,
      title = excluded.title,
      author = excluded.author,
      publish_date = excluded.publish_date,
      summary = excluded.summary,
      key_points_json = excluded.key_points_json,
      word_count = excluded.word_count,
      was_enriched = excluded.was_enriched,
      preview_text = excluded.preview_text
  `);

  stmt.run({
    id,
    user_id: userId,
    timestamp,
    url: item.url,
    title: item.title,
    author: item.author ?? null,
    publish_date: item.publishDate ?? null,
    summary: item.summary,
    key_points_json: JSON.stringify(Array.isArray(item.keyPoints) ? item.keyPoints : []),
    word_count: item.wordCount,
    was_enriched: item.wasEnriched ? 1 : 0,
    preview_text: previewText,
  });

  return {
    id,
    timestamp,
    url: item.url,
    title: item.title,
    author: item.author,
    publishDate: item.publishDate,
    summary: item.summary,
    keyPoints: Array.isArray(item.keyPoints) ? item.keyPoints : [],
    wordCount: item.wordCount,
    wasEnriched: !!item.wasEnriched,
    previewText,
  };
}

export function listHistory(userId: string, limit = 50): PersistedHistoryItem[] {
  const db = getDb();
  const stmt = db.prepare(`
    SELECT id, timestamp, url, title, author, publish_date, summary,
           key_points_json, word_count, was_enriched, preview_text
      FROM history
     WHERE user_id = ?
     ORDER BY timestamp DESC
     LIMIT ?
  `);

  const rows = stmt.all(userId, limit) as Array<{
    id: string;
    timestamp: number;
    url: string;
    title: string;
    author: string | null;
    publish_date: string | null;
    summary: string;
    key_points_json: string;
    word_count: number;
    was_enriched: number;
    preview_text: string;
  }>;

  return rows.map((r) => ({
    id: r.id,
    timestamp: Number(r.timestamp),
    url: r.url,
    title: r.title,
    author: r.author ?? undefined,
    publishDate: r.publish_date ?? undefined,
    summary: r.summary,
    keyPoints: (() => {
      try {
        const parsed = JSON.parse(r.key_points_json);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    })(),
    wordCount: Number(r.word_count),
    wasEnriched: !!r.was_enriched,
    previewText: r.preview_text,
  }));
}

export function deleteHistoryItem(userId: string, id: string): boolean {
  const db = getDb();
  const stmt = db.prepare(`DELETE FROM history WHERE user_id = ? AND id = ?`);
  const res = stmt.run(userId, id);
  return res.changes > 0;
}

export function clearHistory(userId: string): number {
  const db = getDb();
  const stmt = db.prepare(`DELETE FROM history WHERE user_id = ?`);
  const res = stmt.run(userId);
  return res.changes;
}
