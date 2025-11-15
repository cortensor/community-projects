export type AssetType = 'equity' | 'crypto' | 'forex' | 'etf' | 'commodity';

export type AnalysisHorizon = '1W' | '1M' | '3M' | '6M' | '1Y';

export interface HistoricalCandle {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
}

export interface TechnicalSummary {
  sma20?: number;
  sma50?: number;
  sma200?: number;
  ema20?: number;
  rsi14?: number;
  macd?: number;
  macdSignal?: number;
  macdHistogram?: number;
  volatility?: number;
  supportLevel?: number;
  resistanceLevel?: number;
  volumeTrend?: number;
}

export interface FundamentalSnapshot {
  marketCap?: number;
  peRatio?: number;
  pbRatio?: number;
  dividendYield?: number;
  revenueGrowth?: number;
  grossMargin?: number;
  operatingMargin?: number;
  netMargin?: number;
  eps?: number;
  freeCashFlow?: number;
}

export interface MarketNewsItem {
  title: string;
  url: string;
  source: string;
  summary?: string;
  publishedAt: string;
  sentiment?: 'positive' | 'neutral' | 'negative';
}

export interface MarketSnapshot {
  ticker: string;
  assetType: AssetType;
  companyName?: string;
  exchange?: string;
  currency?: string;
  sector?: string;
  industry?: string;
  country?: string;
  latestPrice?: number;
  open?: number;
  high?: number;
  low?: number;
  previousClose?: number;
  change?: number;
  changePercent?: number;
  volume?: number;
  averageVolume?: number;
  marketCap?: number;
  beta?: number;
  lastUpdated?: string;
}

export interface CatalystHighlight {
  label: string;
  description: string;
  impact?: 'high' | 'medium' | 'low';
}

export interface MarketAnalysisContext {
  snapshot: MarketSnapshot;
  horizon: AnalysisHorizon;
  technicals: TechnicalSummary;
  fundamentals: FundamentalSnapshot;
  history: HistoricalCandle[];
  news: MarketNewsItem[];
  catalysts: CatalystHighlight[];
}

export interface AIAnalysis {
  narrative: string;
  keyPoints: string[];
  opportunities: string[];
  risks: string[];
  confidence?: 'low' | 'medium' | 'high';
  nextSteps?: string[];
  horizonNote?: string;
}

export interface AnalyzerResponse {
  meta: MarketSnapshot & { horizon: AnalysisHorizon };
  technicals: TechnicalSummary;
  fundamentals: FundamentalSnapshot;
  history: HistoricalCandle[];
  news: MarketNewsItem[];
  catalysts: CatalystHighlight[];
  ai: AIAnalysis;
}
