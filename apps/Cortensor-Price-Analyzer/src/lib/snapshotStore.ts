import type {
  CategorySnapshot,
  MarketTickerItem,
  QuoteProvider,
  WatchlistKey,
} from '@/app/api/market-tickers/route';
import { snapshotDb } from './db/client';

const INSERT_SNAPSHOT = snapshotDb.prepare(`
  INSERT INTO market_snapshots (category, provider, payload, refreshed_at)
  VALUES (@category, @provider, @payload, @refreshedAt)
`);

const SELECT_LATEST = snapshotDb.prepare(`
  SELECT provider, payload, refreshed_at AS refreshedAt, created_at AS createdAt
  FROM market_snapshots
  WHERE category = @category
  ORDER BY created_at DESC
  LIMIT 1
`);

export type PersistedSnapshot = {
  category: WatchlistKey;
  provider: QuoteProvider;
  items: MarketTickerItem[];
  refreshedAt: string | null;
  createdAt: string;
};

class SnapshotStore {
  saveSnapshot(category: WatchlistKey, snapshot: Pick<CategorySnapshot, 'items' | 'provider' | 'refreshedAt'>): void {
    try {
      INSERT_SNAPSHOT.run({
        category,
        provider: snapshot.provider,
        payload: JSON.stringify(snapshot.items),
        refreshedAt: snapshot.refreshedAt ?? null,
      });
    } catch (error) {
      console.error('Failed to persist market snapshot', error);
    }
  }

  getLatestSnapshot(category: WatchlistKey): PersistedSnapshot | null {
    try {
      const row = SELECT_LATEST.get({ category }) as
        | { provider: string; payload: string; refreshedAt: string | null; createdAt: string }
        | undefined;
      if (!row) {
        return null;
      }
      return {
        category,
        provider: row.provider as QuoteProvider,
        items: parseItems(row.payload),
        refreshedAt: row.refreshedAt ?? null,
        createdAt: row.createdAt,
      };
    } catch (error) {
      console.error('Failed to load market snapshot', error);
      return null;
    }
  }

  getSnapshotWithinTtl(category: WatchlistKey, ttlMs: number): PersistedSnapshot | null {
    const snapshot = this.getLatestSnapshot(category);
    if (!snapshot) {
      return null;
    }

    return isWithinTtl(snapshot.createdAt, ttlMs) ? snapshot : null;
  }
}

function parseItems(payload: string): MarketTickerItem[] {
  try {
    const parsed = JSON.parse(payload);
    return Array.isArray(parsed) ? (parsed as MarketTickerItem[]) : [];
  } catch (error) {
    console.error('Failed to parse snapshot payload', error);
    return [];
  }
}

function isWithinTtl(createdAtIso: string, ttlMs: number): boolean {
  const createdAt = Date.parse(createdAtIso);
  if (!Number.isFinite(createdAt)) {
    return false;
  }
  return Date.now() - createdAt <= ttlMs;
}

export const snapshotStore = new SnapshotStore();
