import type { AnalysisHorizon, AnalyzerResponse, AssetType } from './marketTypes';

export interface HistoryItem {
  id: string;
  timestamp: number;
  ticker: string;
  assetType: AssetType;
  horizon: AnalysisHorizon;
  companyName?: string;
  latestPrice?: number;
  changePercent?: number;
  report: AnalyzerResponse;
  previewText: string;
}

interface SaveHistoryPayload {
  report: AnalyzerResponse;
}

const HISTORY_KEY = 'price_analyzer_history';
const MAX_HISTORY_ITEMS = 75;

export class HistoryService {
  static getHistory(): HistoryItem[] {
    if (typeof window === 'undefined') return [];
    try {
      const stored = window.localStorage.getItem(HISTORY_KEY);
      if (!stored) return [];
      const items = JSON.parse(stored) as HistoryItem[];
      return items.sort((a, b) => b.timestamp - a.timestamp);
    } catch (error) {
      console.error('Error loading history:', error);
      return [];
    }
  }

  static saveToHistory(payload: SaveHistoryPayload): void {
    if (typeof window === 'undefined') return;
    try {
      const history = this.getHistory();
      const { report } = payload;

      const newItem: HistoryItem = {
        id: this.generateId(),
        timestamp: Date.now(),
        ticker: report.meta.ticker,
        assetType: report.meta.assetType,
        horizon: report.meta.horizon,
        companyName: report.meta.companyName,
        latestPrice: report.meta.latestPrice,
        changePercent: report.meta.changePercent,
        report,
        previewText: this.createPreview(report.ai.narrative),
      };

      const existingIndex = history.findIndex(
        (item) =>
          item.ticker === report.meta.ticker &&
          item.horizon === report.meta.horizon &&
          item.assetType === report.meta.assetType,
      );

      if (existingIndex !== -1) {
        history[existingIndex] = newItem;
      } else {
        history.unshift(newItem);
      }

      const limited = history.slice(0, MAX_HISTORY_ITEMS);
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(limited));
    } catch (error) {
      console.error('Error saving to history:', error);
    }
  }

  static deleteHistoryItem(id: string): void {
    if (typeof window === 'undefined') return;
    try {
      const history = this.getHistory();
      const filtered = history.filter((item) => item.id !== id);
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(filtered));
    } catch (error) {
      console.error('Error deleting history item:', error);
    }
  }

  static clearHistory(): void {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.removeItem(HISTORY_KEY);
    } catch (error) {
      console.error('Error clearing history:', error);
    }
  }

  static searchHistory(query: string): HistoryItem[] {
    const lowered = query.toLowerCase();
    return this.getHistory().filter((item) => {
      const { report } = item;
      return (
        item.ticker.toLowerCase().includes(lowered) ||
        (item.companyName && item.companyName.toLowerCase().includes(lowered)) ||
        report.ai.narrative.toLowerCase().includes(lowered) ||
  report.ai.keyPoints.some((point: string) => point.toLowerCase().includes(lowered))
      );
    });
  }

  static getHistoryStats(): { total: number; oldestDate: Date | null } {
    const history = this.getHistory();
    return {
      total: history.length,
      oldestDate: history.length ? new Date(Math.min(...history.map((item) => item.timestamp))) : null,
    };
  }

  private static generateId(): string {
    return `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
  }

  private static createPreview(text: string): string {
    const clean = text.replace(/\s+/g, ' ').trim();
    return clean.length > 180 ? `${clean.slice(0, 177)}...` : clean;
  }
}