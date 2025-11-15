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

export class HistoryService {
  static getHistory(): HistoryItem[] {
    try {
      const stored = localStorage.getItem(HISTORY_KEY);
      if (!stored) return [];
      
      const items = JSON.parse(stored) as HistoryItem[];
      // Sort by timestamp descending (newest first)
      return items.sort((a, b) => b.timestamp - a.timestamp);
    } catch (error) {
      console.error('Error loading history:', error);
      return [];
    }
  }

  static saveToHistory(item: Omit<HistoryItem, 'id' | 'timestamp' | 'previewText'>): void {
    try {
      const history = this.getHistory();
      
      // Create new history item
      const newItem: HistoryItem = {
        ...item,
        id: this.generateId(),
        timestamp: Date.now(),
        previewText: this.createPreview(item.summary)
      };

      // Check if URL already exists (avoid duplicates)
      const existingIndex = history.findIndex(h => h.url === item.url);
      if (existingIndex !== -1) {
        // Update existing item
        history[existingIndex] = newItem;
      } else {
        // Add new item to beginning
        history.unshift(newItem);
      }

      // Limit history size
      const limitedHistory = history.slice(0, MAX_HISTORY_ITEMS);
      
      localStorage.setItem(HISTORY_KEY, JSON.stringify(limitedHistory));
    } catch (error) {
      console.error('Error saving to history:', error);
    }
  }

  static getHistoryItem(id: string): HistoryItem | null {
    const history = this.getHistory();
    return history.find(item => item.id === id) || null;
  }

  static deleteHistoryItem(id: string): void {
    try {
      const history = this.getHistory();
      const filtered = history.filter(item => item.id !== id);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(filtered));
    } catch (error) {
      console.error('Error deleting history item:', error);
    }
  }

  static clearHistory(): void {
    try {
      localStorage.removeItem(HISTORY_KEY);
    } catch (error) {
      console.error('Error clearing history:', error);
    }
  }

  static searchHistory(query: string): HistoryItem[] {
    const history = this.getHistory();
    const lowercaseQuery = query.toLowerCase();
    
    return history.filter(item => 
      item.title.toLowerCase().includes(lowercaseQuery) ||
      item.url.toLowerCase().includes(lowercaseQuery) ||
      item.summary.toLowerCase().includes(lowercaseQuery) ||
      (item.author && item.author.toLowerCase().includes(lowercaseQuery))
    );
  }

  static getHistoryStats(): { totalItems: number; totalArticles: number; oldestDate: Date | null } {
    const history = this.getHistory();
    return {
      totalItems: history.length,
      totalArticles: history.length,
      oldestDate: history.length > 0 ? new Date(Math.min(...history.map(h => h.timestamp))) : null
    };
  }

  private static generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }

  private static createPreview(summary: string): string {
    const cleanText = summary.replace(/\n+/g, ' ').trim();
    return cleanText.length > 150 ? cleanText.substring(0, 147) + '...' : cleanText;
  }
}