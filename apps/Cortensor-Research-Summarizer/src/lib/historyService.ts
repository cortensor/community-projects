// src/lib/historyService.ts
export interface HistoryItem {
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
  previewText: string; // First 150 chars of summary for preview
}

const HISTORY_KEY = 'summarizer_history';
const MAX_HISTORY_ITEMS = 50; // Limit to prevent localStorage from getting too large

function createPreview(summary: string): string {
  const cleanText = (summary || '').replace(/\s+/g, ' ').trim();
  return cleanText.length > 150 ? `${cleanText.substring(0, 150)}…` : cleanText;
}

function safeParseHistory(value: string | null): HistoryItem[] {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? (parsed as HistoryItem[]) : [];
  } catch {
    return [];
  }
}

function sortNewestFirst(items: HistoryItem[]): HistoryItem[] {
  return [...items].sort((a, b) => b.timestamp - a.timestamp);
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || res.statusText);
  }
  return (await res.json()) as T;
}

function normalizeUserId(userId: string | null | undefined): string {
  return (typeof userId === 'string' ? userId : '').trim();
}

export class HistoryService {
  static getLocalHistory(): HistoryItem[] {
    try {
      const items = safeParseHistory(localStorage.getItem(HISTORY_KEY));
      return sortNewestFirst(items).slice(0, MAX_HISTORY_ITEMS);
    } catch (error) {
      console.error('Error loading local history:', error);
      return [];
    }
  }

  static async getHistory(userId?: string | null): Promise<HistoryItem[]> {
    const uid = normalizeUserId(userId);
    if (!uid) return this.getLocalHistory();

    try {
      const data = await fetchJson<{ items: HistoryItem[] }>(`/api/history?userId=${encodeURIComponent(uid)}`, {
        cache: 'no-store'
      });
      const items = Array.isArray(data.items) ? data.items : [];
      return sortNewestFirst(items).slice(0, MAX_HISTORY_ITEMS);
    } catch (error) {
      console.warn('History API unavailable, falling back to local history:', error);
      return this.getLocalHistory();
    }
  }

  static saveLocalToHistory(item: Omit<HistoryItem, 'id' | 'timestamp' | 'previewText'>): HistoryItem {
    const history = this.getLocalHistory();
    const newItem: HistoryItem = {
      ...item,
      id: this.generateId(),
      timestamp: Date.now(),
      previewText: createPreview(item.summary)
    };

    const existingIndex = history.findIndex(h => h.url === item.url);
    if (existingIndex !== -1) {
      history[existingIndex] = newItem;
    } else {
      history.unshift(newItem);
    }

    const limited = history.slice(0, MAX_HISTORY_ITEMS);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(limited));
    return newItem;
  }

  static async saveToHistory(
    userId: string | null | undefined,
    item: Omit<HistoryItem, 'id' | 'timestamp' | 'previewText'>
  ): Promise<HistoryItem> {
    const localItem = this.saveLocalToHistory(item);
    const uid = normalizeUserId(userId);
    if (!uid) return localItem;

    try {
      const data = await fetchJson<{ success: boolean; item: HistoryItem }>(`/api/history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: uid,
          item: {
            timestamp: localItem.timestamp,
            url: item.url,
            title: item.title,
            author: item.author,
            publishDate: item.publishDate,
            summary: item.summary,
            keyPoints: item.keyPoints,
            wordCount: item.wordCount,
            wasEnriched: item.wasEnriched
          }
        })
      });
      return data.item ?? localItem;
    } catch (error) {
      console.warn('Failed to persist history to server:', error);
      return localItem;
    }
  }

  static getHistoryItemLocal(id: string): HistoryItem | null {
    const history = this.getLocalHistory();
    return history.find(item => item.id === id) || null;
  }

  static deleteLocalHistoryItem(id: string): void {
    try {
      const history = this.getLocalHistory();
      const filtered = history.filter(item => item.id !== id);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(filtered));
    } catch (error) {
      console.error('Error deleting local history item:', error);
    }
  }

  static async deleteHistoryItem(userId: string | null | undefined, id: string): Promise<void> {
    this.deleteLocalHistoryItem(id);
    const uid = normalizeUserId(userId);
    if (!uid) return;
    try {
      await fetchJson(`/api/history`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: uid, id })
      });
    } catch (error) {
      console.warn('Failed to delete history item on server:', error);
    }
  }

  static clearLocalHistory(): void {
    try {
      localStorage.removeItem(HISTORY_KEY);
    } catch (error) {
      console.error('Error clearing local history:', error);
    }
  }

  static async clearHistory(userId: string | null | undefined): Promise<void> {
    this.clearLocalHistory();
    const uid = normalizeUserId(userId);
    if (!uid) return;
    try {
      await fetchJson(`/api/history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: uid, action: 'clear' })
      });
    } catch (error) {
      console.warn('Failed to clear server history:', error);
    }
  }

  static getHistoryStats(): { totalItems: number; totalArticles: number; oldestDate: Date | null } {
    const history = this.getLocalHistory();
    return {
      totalItems: history.length,
      totalArticles: history.length,
      oldestDate: history.length > 0 ? new Date(Math.min(...history.map(h => h.timestamp))) : null
    };
  }

  private static generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }
}