'use client';

import { useEffect, useMemo, useState } from 'react';
import type { ChangeEvent, ComponentType, FormEvent } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { HistoryPanel } from '@/components/HistoryPanel';
import PriceHistoryChart, { CandleWithClose } from '@/components/PriceHistoryChart';
import { cn } from '@/lib/utils';
import { HistoryService, HistoryItem } from '@/lib/historyService';
import {
  AnalysisHorizon,
  AnalyzerResponse,
  AssetType,
  MarketNewsItem,
  TechnicalSummary,
  FundamentalSnapshot,
  CatalystHighlight,
  HistoricalCandle,
} from '@/lib/marketTypes';
import {
  ActivitySquare,
  AlertTriangle,
  ArrowRight,
  Brain,
  ClipboardCopy,
  Clock,
  Download,
  LineChart,
  ListChecks,
  Loader2,
  Info,
  Newspaper,
  Sparkles,
  Target,
  TrendingUp,
  TrendingDown,
  Zap,
  PanelRightClose,
  History as HistoryIcon,
} from 'lucide-react';

interface LoadingStep {
  id: string;
  title: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  status: 'pending' | 'active' | 'completed' | 'error';
}

interface TechnicalMetric {
  label: string;
  value?: number;
  format?: (value?: number) => string;
  extra?: number;
}

interface FundamentalMetric {
  label: string;
  value?: number;
  formatter?: (value?: number) => string;
}

const assetTypeOptions: { value: AssetType; label: string }[] = [
  { value: 'equity', label: 'Equity' },
  { value: 'etf', label: 'ETF' },
  { value: 'crypto', label: 'Crypto' },
  { value: 'forex', label: 'Forex Pair' },
  { value: 'commodity', label: 'Commodity' },
];

const horizonOptions: { value: AnalysisHorizon; label: string }[] = [
  { value: '1W', label: '1 Week' },
  { value: '1M', label: '1 Month' },
  { value: '3M', label: '3 Months' },
  { value: '6M', label: '6 Months' },
  { value: '1Y', label: '1 Year' },
];

const impactColorMap: Record<NonNullable<CatalystHighlight['impact']>, string> = {
  high: 'bg-red-100 text-red-700 border-red-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  low: 'bg-slate-100 text-slate-700 border-slate-200',
};

const sentimentColorMap: Record<'positive' | 'neutral' | 'negative', string> = {
  positive: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  neutral: 'bg-slate-100 text-slate-700 border-slate-200',
  negative: 'bg-red-100 text-red-700 border-red-200',
};

const FOREX_PATTERN = /^[A-Z]{3}\/[A-Z]{3}$/;
const knownCryptoSymbols = new Set([
  'APT',
  'APTOS',
  'ARB',
  'ARBITRUM',
  'ATOM',
  'AVAX',
  'AVALANCHE',
  'ALGO',
  'ALGORAND',
  'BNB',
  'BUSD',
  'BTC',
  'XBT',
  'BITCOIN',
  'BCH',
  'BITCOINCASH',
  'CELESTIA',
  'CHAINLINK',
  'COSMOS',
  'DAI',
  'DOGE',
  'DOGECOIN',
  'DOT',
  'ETH',
  'ETHEREUM',
  'ETC',
  'ETHEREUMCLASSIC',
  'LINK',
  'LTC',
  'LITECOIN',
  'MATIC',
  'NEAR',
  'OP',
  'OPTIMISM',
  'POLYGON',
  'POLKADOT',
  'RIPPLE',
  'SOL',
  'SOLANA',
  'SHIB',
  'SHIBA',
  'SHIBAINU',
  'SUI',
  'STETH',
  'TIA',
  'TRX',
  'TRON',
  'UNI',
  'UNISWAP',
  'USDC',
  'USDCOIN',
  'USDT',
  'TETHER',
  'WBTC',
]);

const commodityTickers = new Set([
  'GC=F',
  'SI=F',
  'PL=F',
  'HG=F',
  'CL=F',
  'NG=F',
  'ZS=F',
  'ZC=F',
  'ZW=F',
  'KC=F',
  'SB=F',
  'CT=F',
  'CC=F',
]);

function inferAssetTypeFromTicker(input: string): AssetType | null {
  const symbol = input.trim().toUpperCase();
  if (!symbol) return null;

  const sanitized = symbol.replace(/[^A-Z0-9]/g, '');

  if (symbol.startsWith('CRYPTO:')) {
    return 'crypto';
  }

  if (FOREX_PATTERN.test(symbol)) {
    return 'forex';
  }

  if (knownCryptoSymbols.has(symbol) || knownCryptoSymbols.has(sanitized) || symbol.endsWith('USDT') || symbol.endsWith('USDC')) {
    return 'crypto';
  }

  if (symbol.includes('USDT/') || symbol.includes('USD/USDT')) {
    return 'crypto';
  }

  const fiatSuffixes = ['USD', 'USDT', 'USDC', 'EUR', 'GBP'];
  for (const suffix of fiatSuffixes) {
    if (sanitized.endsWith(suffix) && sanitized.length > suffix.length) {
      const base = sanitized.slice(0, -suffix.length);
      if (knownCryptoSymbols.has(base)) {
        return 'crypto';
      }
    }
  }

  if (commodityTickers.has(symbol) || symbol.endsWith('=F')) {
    return 'commodity';
  }

  return null;
}

function formatNewsDate(dateInput: string): string {
  const date = new Date(dateInput);
  if (Number.isNaN(date.getTime())) {
    return dateInput;
  }
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatHistoryDate(dateInput: string): string {
  const date = new Date(dateInput);
  if (Number.isNaN(date.getTime())) {
    return dateInput;
  }
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatNumber(value?: number, digits = 2): string {
  if (value === undefined || value === null || Number.isNaN(value)) return '—';
  if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(digits)}B`;
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(digits)}M`;
  if (Math.abs(value) >= 1e3) return `${(value / 1e3).toFixed(digits)}K`;
  return value.toFixed(digits);
}

function formatPercent(value?: number, digits = 2): string {
  if (value === undefined || value === null || Number.isNaN(value)) return '—';
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}%`;
}

function getTechnicalPairs(technicals: TechnicalSummary): TechnicalMetric[] {
  return [
    { label: 'SMA20', value: technicals.sma20 },
    { label: 'SMA50', value: technicals.sma50 },
    { label: 'SMA200', value: technicals.sma200 },
    { label: 'EMA20', value: technicals.ema20 },
    { label: 'RSI 14', value: technicals.rsi14, format: (v?: number) => (v ? v.toFixed(1) : '—') },
    { label: 'MACD', value: technicals.macd, extra: technicals.macdSignal },
    { label: 'Volatility (ann.)', value: technicals.volatility, format: (v?: number) => (v ? `${(v * 100).toFixed(1)}%` : '—') },
    { label: 'Volume Trend', value: technicals.volumeTrend, format: (v?: number) => (v ? v.toFixed(2) : '—') },
    { label: 'Support (30d)', value: technicals.supportLevel },
    { label: 'Resistance (30d)', value: technicals.resistanceLevel },
  ];
}

function getFundamentalPairs(fundamentals: FundamentalSnapshot): FundamentalMetric[] {
  return [
    { label: 'Market Cap', value: fundamentals.marketCap, formatter: formatNumber },
    { label: 'P/E Ratio', value: fundamentals.peRatio, formatter: (v?: number) => (v ? v.toFixed(2) : '—') },
    { label: 'P/B Ratio', value: fundamentals.pbRatio, formatter: (v?: number) => (v ? v.toFixed(2) : '—') },
    { label: 'Dividend Yield', value: fundamentals.dividendYield, formatter: (v?: number) => (v ? `${(v * 100).toFixed(2)}%` : '—') },
    { label: 'Revenue Growth', value: fundamentals.revenueGrowth, formatter: (v?: number) => (v ? `${(v * 100).toFixed(2)}%` : '—') },
    { label: 'Gross Margin', value: fundamentals.grossMargin, formatter: (v?: number) => (v ? `${(v * 100).toFixed(2)}%` : '—') },
    { label: 'Operating Margin', value: fundamentals.operatingMargin, formatter: (v?: number) => (v ? `${(v * 100).toFixed(2)}%` : '—') },
    { label: 'Net Margin', value: fundamentals.netMargin, formatter: (v?: number) => (v ? `${(v * 100).toFixed(2)}%` : '—') },
    { label: 'EPS (TTM)', value: fundamentals.eps, formatter: (v?: number) => (v ? v.toFixed(2) : '—') },
    { label: 'FCF / Share', value: fundamentals.freeCashFlow, formatter: (v?: number) => (v ? v.toFixed(2) : '—') },
  ];
}

const defaultSteps: LoadingStep[] = [
  {
    id: 'ingest',
    title: 'Market Data Collection',
    description: 'Pulling price, volume, and reference data',
    icon: TrendingUp,
    status: 'pending',
  },
  {
    id: 'technicals',
    title: 'Technical Scan',
    description: 'Computing moving averages, RSI, MACD, and volatility',
    icon: ActivitySquare,
    status: 'pending',
  },
  {
    id: 'fundamentals',
    title: 'Fundamentals & News',
    description: 'Aggregating valuation metrics and latest headlines',
    icon: Newspaper,
    status: 'pending',
  },
  {
    id: 'ai',
    title: 'AI Synthesis',
    description: 'Generating institutional-grade narrative with Cortensor',
    icon: Brain,
    status: 'pending',
  },
];

export default function PriceAnalyzerForm() {
  const [ticker, setTicker] = useState('');
  const [assetType, setAssetType] = useState<AssetType>('equity');
  const [horizon, setHorizon] = useState<AnalysisHorizon>('3M');
  const [assetTypeManuallySelected, setAssetTypeManuallySelected] = useState(false);
  const [result, setResult] = useState<AnalyzerResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [steps, setSteps] = useState<LoadingStep[]>(defaultSteps);
  const [showHistory, setShowHistory] = useState(false);
  const [historyCount, setHistoryCount] = useState(0);

  const historySeries = useMemo<CandleWithClose[]>(() => {
    if (!result) return [];
    return result.history
      .filter((entry): entry is CandleWithClose => typeof entry.close === 'number' && !!entry.date && Number.isFinite(entry.close))
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }, [result]);

  const historyStart = historySeries[0]?.close ?? null;
  const historyEnd = historySeries.length > 0 ? historySeries[historySeries.length - 1].close : null;
  const historyChange = historyStart !== null && historyEnd !== null ? historyEnd - historyStart : null;
  const historyChangePercent = historyStart && historyStart !== 0 && historyChange !== null
    ? (historyChange / historyStart) * 100
    : null;
  const historyRangeLabel = historySeries.length > 1
    ? `${formatHistoryDate(historySeries[0].date)} → ${formatHistoryDate(historySeries[historySeries.length - 1].date)}`
    : historySeries.length === 1
      ? formatHistoryDate(historySeries[0].date)
      : '—';
  const historyTrendUp = (historyChange ?? 0) >= 0;
  const fundamentalPairs = useMemo(() => (result ? getFundamentalPairs(result.fundamentals) : []), [result]);
  const hasFundamentals = fundamentalPairs.some(({ value }) => value !== undefined && value !== null);
  const technicalPairs = useMemo(() => (result ? getTechnicalPairs(result.technicals) : []), [result]);
  const hasTechnicals = technicalPairs.some(({ value, extra }) => (value ?? extra) !== undefined && (value ?? extra) !== null);

  useEffect(() => {
    setHistoryCount(HistoryService.getHistory().length);
  }, []);

  useEffect(() => {
    if (!ticker.trim()) {
      setAssetTypeManuallySelected(false);
    }
  }, [ticker]);

  const resetSteps = () => {
    setSteps(defaultSteps.map((step: LoadingStep) => ({ ...step, status: 'pending' })));
    setProgress(0);
  };

  const updateStep = (stepId: string, status: LoadingStep['status'], completedIndex?: number) => {
    setSteps((prev: LoadingStep[]) =>
      prev.map((step: LoadingStep) => (step.id === stepId ? { ...step, status } : step)),
    );
    if (status === 'completed' && typeof completedIndex === 'number') {
      const completion = Math.round(((completedIndex + 1) / defaultSteps.length) * 100);
      setProgress(completion);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!ticker.trim()) return;

    resetSteps();
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      updateStep('ingest', 'active');
      await new Promise((resolve) => setTimeout(resolve, 300));
      updateStep('ingest', 'completed', 0);

      updateStep('technicals', 'active');

      const response = await fetch('/api/price-analyzer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, assetType, horizon }),
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.statusText}`);
      }

      const payload = await response.json();
      const data: AnalyzerResponse = payload.data;

      updateStep('technicals', 'completed', 1);

      updateStep('fundamentals', 'active');
      await new Promise((resolve) => setTimeout(resolve, 250));
      updateStep('fundamentals', 'completed', 2);

      updateStep('ai', 'active');
      await new Promise((resolve) => setTimeout(resolve, 200));
      updateStep('ai', 'completed', 3);

      setResult(data);
      setProgress(100);

      HistoryService.saveToHistory({ report: data });
      setHistoryCount(HistoryService.getHistory().length);
    } catch (err) {
      console.error(err);
      const message = err instanceof Error ? err.message : 'Unexpected error';
      setError(message);
      setSteps((prev: LoadingStep[]) =>
        prev.map((step: LoadingStep) => (step.status === 'active' ? { ...step, status: 'error' } : step)),
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadHistory = (item: HistoryItem) => {
    setResult(item.report);
    setTicker(item.report.meta.ticker);
    setAssetType(item.report.meta.assetType);
    setHorizon(item.report.meta.horizon);
    setError(null);
    setProgress(100);
    setSteps(defaultSteps.map((step: LoadingStep) => ({ ...step, status: 'completed' })));

    setTimeout(() => {
      const node = document.getElementById('results-section');
      if (node) {
        node.scrollIntoView({ behavior: 'smooth' });
      }
    }, 150);
  };

  const handleCopyJson = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    } catch (copyError) {
      console.error('Failed to copy analysis JSON', copyError);
    }
  };

  const handleExportMarkdown = () => {
    if (!result) return;
    const { meta, ai, technicals, fundamentals, catalysts, news } = result;
    const markdown = `# ${meta.ticker} · Price Intelligence (${meta.horizon})\n\n` +
      `**Asset Type:** ${meta.assetType.toUpperCase()}  \n` +
      `**Company:** ${meta.companyName || 'N/A'}  \n` +
      `**Last Price:** ${meta.latestPrice !== undefined ? `$${meta.latestPrice.toFixed(2)}` : 'N/A'}  \n` +
      `**Change:** ${formatNumber(meta.change)} (${formatPercent(meta.changePercent)})  \n` +
      `**Exchange:** ${meta.exchange || 'N/A'}  \n` +
      `**Currency:** ${meta.currency || 'USD'}\n\n` +
      `## Narrative\n${ai.narrative}\n\n` +
  `## Key Points\n${ai.keyPoints.map((point: string) => `- ${point}`).join('\n')}\n\n` +
  (ai.opportunities.length ? `## Opportunities\n${ai.opportunities.map((point: string) => `- ${point}`).join('\n')}\n\n` : '') +
  (ai.risks.length ? `## Risks\n${ai.risks.map((point: string) => `- ${point}`).join('\n')}\n\n` : '') +
  (ai.nextSteps && ai.nextSteps.length ? `## Suggested Next Steps\n${ai.nextSteps.map((step: string) => `- ${step}`).join('\n')}\n\n` : '') +
      (ai.horizonNote ? `> ${ai.horizonNote}\n\n` : '') +
      `## Technicals\n` +
      getTechnicalPairs(technicals)
        .map(({ label, value, format, extra }) => `- ${label}: ${format ? format(value) : formatNumber(value)}${extra ? ` (signal: ${formatNumber(extra)})` : ''}`)
        .join('\n') +
      '\n\n## Fundamentals\n' +
      getFundamentalPairs(fundamentals)
        .map(({ label, value, formatter }) => `- ${label}: ${formatter ? formatter(value) : formatNumber(value)}`)
        .join('\n') +
      '\n\n## Catalysts\n' +
  (catalysts.length ? catalysts.map((catalyst: CatalystHighlight) => `- ${catalyst.label}${catalyst.impact ? ` (${catalyst.impact})` : ''}: ${catalyst.description}`).join('\n') : 'No catalysts detected') +
      '\n\n## Headlines\n' +
  (news.length ? news.map((item: MarketNewsItem) => `- [${item.sentiment?.toUpperCase() || 'NEUTRAL'}] ${item.title} (${item.source} – ${formatNewsDate(item.publishedAt)})`).join('\n') : 'No recent headlines');

    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${meta.ticker}-price-analysis.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const recentHistory: HistoricalCandle[] = result ? [...result.history].slice(-10).reverse() : [];

  return (
    <div className="min-h-screen w-full">
      <div className="max-w-7xl mx-auto p-4 sm:p-6 md:p-8 space-y-6 md:space-y-8">
        <div className="text-center space-y-3 sm:space-y-4">
          <div className="flex items-center justify-center space-x-2">
            <Sparkles className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent">
              Price Analyzer
            </h1>
          </div>
          <p className="text-sm sm:text-base md:text-lg text-muted-foreground max-w-2xl mx-auto">
            Fuse multi-source market data and Cortensor intelligence to get actionable price context across equities, crypto, forex, and ETFs.
          </p>
          <div className="flex justify-center">
            <Button
              variant="outline"
              onClick={() => setShowHistory((prev: boolean) => !prev)}
              className="flex items-center space-x-2 text-sm hover:bg-blue-50"
            >
              {showHistory ? (
                <>
                  <PanelRightClose className="h-4 w-4" />
                  <span>Hide History</span>
                </>
              ) : (
                <>
                  <HistoryIcon className="h-4 w-4" />
                  <span>Show Saved Analyses</span>
                  {historyCount > 0 && (
                    <Badge variant="secondary" className="ml-1 text-xs">
                      {historyCount}
                    </Badge>
                  )}
                </>
              )}
            </Button>
          </div>
        </div>

        <div
          className={cn(
            'grid gap-6 transition-all duration-300',
            showHistory ? 'grid-cols-1 lg:grid-cols-3' : 'grid-cols-1',
          )}
        >
          <div
            className={cn(
              'space-y-6',
              showHistory ? 'lg:col-span-2' : 'max-w-4xl mx-auto w-full',
            )}
          >
            <Card className="border-2 shadow-sm">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center space-x-2">
                  <LineChart className="h-5 w-5" />
                  <span>Run a Price Analysis</span>
                </CardTitle>
                <CardDescription>
                  Provide a ticker, asset type, and horizon to generate a complete market brief.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-4">
                  <div className="md:col-span-2 space-y-2">
                    <label className="text-sm font-medium text-slate-700" htmlFor="ticker">
                      Ticker / Symbol
                    </label>
                    <Input
                      id="ticker"
                      placeholder="e.g. NVDA, BTC, EUR/USD"
                      value={ticker}
                      onChange={(event: ChangeEvent<HTMLInputElement>) => {
                        const nextValue = event.target.value.toUpperCase();
                        setTicker(nextValue);

                        if (!assetTypeManuallySelected) {
                          const inferred = inferAssetTypeFromTicker(nextValue);
                          if (inferred && inferred !== assetType) {
                            setAssetType(inferred);
                          }
                        }
                      }}
                      disabled={isLoading}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700" htmlFor="asset-type">
                      Asset Type
                    </label>
                    <select
                      id="asset-type"
                      value={assetType}
                      onChange={(event: ChangeEvent<HTMLSelectElement>) => {
                        setAssetType(event.target.value as AssetType);
                        setAssetTypeManuallySelected(true);
                      }}
                      disabled={isLoading}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {assetTypeOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700" htmlFor="horizon">
                      Analysis Horizon
                    </label>
                    <select
                      id="horizon"
                      value={horizon}
                      onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                        setHorizon(event.target.value as AnalysisHorizon)
                      }
                      disabled={isLoading}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {horizonOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="md:col-span-4">
                    <Button
                      type="submit"
                      disabled={isLoading || !ticker.trim()}
                      className="w-full h-11 text-sm font-semibold"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                          Building market intelligence...
                        </>
                      ) : (
                        <>
                          <Zap className="mr-2 h-5 w-5" />
                          Analyze Price Action
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>

            {isLoading && (
              <Card className="border-blue-200 bg-blue-50/60">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2 text-blue-700">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Pipeline Progress</span>
                  </CardTitle>
                  <Progress value={progress} className="h-2" />
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-start gap-3 rounded-md border border-blue-200 bg-white/80 p-3 text-sm text-slate-700">
                    <Info className="mt-0.5 h-4 w-4 text-blue-600" />
                    <p>
                      Technical scan and AI synthesis may take 1–3 minutes when the network is busy. Hang tight—we&apos;ll finalize
                      the analysis as soon as the data pipeline completes.
                    </p>
                  </div>
                  {steps.map((step: LoadingStep) => (
                    <div
                      key={step.id}
                      className={cn(
                        'flex items-start space-x-3 rounded-lg border p-3 transition-colors',
                        step.status === 'completed' && 'border-green-200 bg-green-50',
                        step.status === 'active' && 'border-blue-300 bg-blue-100',
                        step.status === 'pending' && 'border-slate-200 bg-white/80 opacity-70',
                        step.status === 'error' && 'border-red-300 bg-red-50',
                      )}
                    >
                      <div
                        className={cn(
                          'rounded-full p-2',
                          step.status === 'completed' && 'bg-green-600 text-white',
                          step.status === 'active' && 'bg-blue-600 text-white animate-pulse',
                          step.status === 'pending' && 'bg-slate-200 text-slate-500',
                          step.status === 'error' && 'bg-red-600 text-white',
                        )}
                      >
                        <step.icon className="h-4 w-4" />
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-slate-800">{step.title}</h4>
                        <p className="text-xs text-slate-600">{step.description}</p>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {result && (
              <div id="results-section" className="space-y-6">
                <Card className="shadow-sm border-slate-200">
                  <CardHeader className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="uppercase tracking-wide">
                          {result.meta.assetType}
                        </Badge>
                        <Badge variant="outline">Horizon: {result.meta.horizon}</Badge>
                        {result.ai.confidence && (
                          <Badge variant="outline">Confidence: {result.ai.confidence}</Badge>
                        )}
                      </div>
                      <h2 className="text-xl font-bold text-slate-900">
                        {result.meta.ticker}
                        {result.meta.companyName ? ` · ${result.meta.companyName}` : ''}
                      </h2>
                      <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
                        <span>Exchange: {result.meta.exchange || 'N/A'}</span>
                        <span>Currency: {result.meta.currency || 'USD'}</span>
                        {result.meta.lastUpdated && (
                          <span className="flex items-center gap-1">
                            <Clock className="h-4 w-4" />
                            {formatNewsDate(result.meta.lastUpdated)}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-start gap-3 md:items-end">
                      <div className="flex items-baseline gap-3">
                        <span className="text-3xl font-semibold text-slate-900">
                          {result.meta.latestPrice !== undefined ? `$${result.meta.latestPrice.toFixed(2)}` : '—'}
                        </span>
                        <span
                          className={cn(
                            'flex items-center gap-1 text-sm font-semibold',
                            (result.meta.changePercent ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-600',
                          )}
                        >
                          {(result.meta.changePercent ?? 0) >= 0 ? (
                            <ArrowRight className="h-4 w-4 rotate-[-45deg]" />
                          ) : (
                            <ArrowRight className="h-4 w-4 rotate-[135deg]" />
                          )}
                          {formatNumber(result.meta.change)} ({formatPercent(result.meta.changePercent)})
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button variant="outline" size="sm" onClick={handleCopyJson}>
                          <ClipboardCopy className="mr-1 h-4 w-4" /> Copy JSON
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleExportMarkdown}>
                          <Download className="mr-1 h-4 w-4" /> Export Markdown
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                </Card>

                <Card className="shadow-sm border-slate-200">
                  <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-center gap-2">
                      <LineChart className="h-5 w-5 text-blue-600" />
                      <CardTitle className="text-base">Price Action</CardTitle>
                    </div>
                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 sm:text-sm">
                      <span>Range: {historyRangeLabel}</span>
                      <span>Start: {historyStart !== null ? `$${historyStart.toFixed(2)}` : '—'}</span>
                      <span>Last: {historyEnd !== null ? `$${historyEnd.toFixed(2)}` : '—'}</span>
                      {historyChangePercent !== null && (
                        <span
                          className={cn(
                            'flex items-center gap-1 font-semibold',
                            historyTrendUp ? 'text-emerald-600' : 'text-red-600',
                          )}
                        >
                          {historyTrendUp ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                          {historyChange !== null
                            ? `${historyChange >= 0 ? '+' : '-'}$${Math.abs(historyChange).toFixed(2)}`
                            : '—'}
                          <span>({formatPercent(historyChangePercent)})</span>
                        </span>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="h-72">
                    {historySeries.length > 1 ? (
                      <PriceHistoryChart data={historySeries} />
                    ) : (
                      <div className="flex h-full flex-col items-center justify-center space-y-2 rounded-lg border border-dashed border-slate-200 bg-slate-50 text-center text-sm text-slate-600">
                        <Info className="h-5 w-5 text-slate-500" />
                        <p className="max-w-sm">
                          Unable to render the price chart because no recent candles were returned. Alpha Vantage free-tier limits can delay
                          history responses—please wait a moment and try again.
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Brain className="h-5 w-5 text-purple-600" />
                      AI Narrative
                    </CardTitle>
                    {result.ai.horizonNote && (
                      <CardDescription>{result.ai.horizonNote}</CardDescription>
                    )}
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-sm leading-relaxed text-slate-800 whitespace-pre-line">
                      {result.ai.narrative}
                    </p>
                    <div className="grid gap-4 md:grid-cols-3">
                      <div className="rounded-lg border p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <ListChecks className="h-4 w-4 text-blue-600" />
                          <span className="text-sm font-semibold">Key Points</span>
                        </div>
                        <ul className="space-y-2 text-sm text-slate-700">
                          {result.ai.keyPoints.map((point: string, index: number) => (
                            <li key={index} className="flex gap-2">
                              <span className="font-semibold text-blue-600">{index + 1}.</span>
                              <span>{point}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div className="rounded-lg border p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <Target className="h-4 w-4 text-emerald-600" />
                          <span className="text-sm font-semibold">Opportunities</span>
                        </div>
                        <ul className="space-y-2 text-sm text-slate-700">
                          {result.ai.opportunities.length ? (
                            result.ai.opportunities.map((item: string, index: number) => (
                              <li key={index} className="flex gap-2">
                                <span className="text-emerald-500">•</span>
                                <span>{item}</span>
                              </li>
                            ))
                          ) : (
                            <li className="text-slate-500">No upside narratives flagged.</li>
                          )}
                        </ul>
                      </div>
                      <div className="rounded-lg border p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <AlertTriangle className="h-4 w-4 text-amber-600" />
                          <span className="text-sm font-semibold">Risks</span>
                        </div>
                        <ul className="space-y-2 text-sm text-slate-700">
                          {result.ai.risks.length ? (
                            result.ai.risks.map((item: string, index: number) => (
                              <li key={index} className="flex gap-2">
                                <span className="text-amber-500">•</span>
                                <span>{item}</span>
                              </li>
                            ))
                          ) : (
                            <li className="text-slate-500">No material risks highlighted.</li>
                          )}
                        </ul>
                      </div>
                    </div>
                    {result.ai.nextSteps && result.ai.nextSteps.length > 0 && (
                      <div className="rounded-lg border p-4 bg-slate-50">
                        <div className="flex items-center gap-2 mb-2">
                          <ArrowRight className="h-4 w-4 text-slate-600" />
                          <span className="text-sm font-semibold">Suggested next steps</span>
                        </div>
                        <ul className="space-y-2 text-sm text-slate-700">
                          {result.ai.nextSteps.map((step: string, index: number) => (
                            <li key={index} className="flex gap-2">
                              <span className="text-slate-500">{index + 1}.</span>
                              <span>{step}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <div className="grid gap-6 md:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <ActivitySquare className="h-5 w-5 text-blue-600" />
                        Technical Landscape
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {hasTechnicals ? (
                        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          {technicalPairs.map(({ label, value, format, extra }: TechnicalMetric) => (
                            <div key={label} className="rounded-lg border p-3">
                              <dt className="text-xs uppercase text-slate-500 tracking-wide">{label}</dt>
                              <dd className="text-sm font-semibold text-slate-800 mt-1">
                                {format ? format(value) : formatNumber(value)}
                                {extra !== undefined && (
                                  <span className="ml-2 text-xs text-slate-500">signal {formatNumber(extra)}</span>
                                )}
                              </dd>
                            </div>
                          ))}
                        </dl>
                      ) : (
                        <div className="flex items-center gap-3 rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                          <Info className="h-4 w-4 text-slate-500" />
                          <span>
                            Unable to calculate technical indicators. Ensure recent price history is available and retry once market data services respond.
                          </span>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <ListChecks className="h-5 w-5 text-emerald-600" />
                        Fundamental Snapshot
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {hasFundamentals ? (
                        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          {fundamentalPairs.map(({ label, value, formatter }: FundamentalMetric) => (
                            <div key={label} className="rounded-lg border p-3">
                              <dt className="text-xs uppercase text-slate-500 tracking-wide">{label}</dt>
                              <dd className="text-sm font-semibold text-slate-800 mt-1">
                                {formatter ? formatter(value) : formatNumber(value)}
                              </dd>
                            </div>
                          ))}
                        </dl>
                      ) : (
                        <div className="flex items-center gap-3 rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                          <Info className="h-4 w-4 text-slate-500" />
                          <span>
                            {result.meta.assetType === 'crypto'
                              ? 'Fundamental metrics are not available for crypto assets.'
                              : 'No fundamental data returned for this asset. Try a different ticker or check your data provider limits.'}
                          </span>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Zap className="h-5 w-5 text-orange-600" />
                      Catalysts & Alerts
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {result.catalysts.length ? (
                      result.catalysts.map((catalyst: CatalystHighlight, index: number) => (
                        <div key={index} className="rounded-lg border p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                          <div>
                            <p className="font-semibold text-slate-800">{catalyst.label}</p>
                            <p className="text-sm text-slate-600">{catalyst.description}</p>
                          </div>
                          {catalyst.impact && (
                            <span className={cn('px-3 py-1 rounded-full border text-xs font-semibold', impactColorMap[catalyst.impact])}>
                              {catalyst.impact.toUpperCase()} IMPACT
                            </span>
                          )}
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-slate-500">No notable catalysts detected in the latest scan.</p>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Newspaper className="h-5 w-5 text-indigo-600" />
                      Recent Headlines
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {result.news.length ? (
                      result.news.map((item: MarketNewsItem, index: number) => (
                        <div key={index} className="rounded-lg border p-4 space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            {item.sentiment && (
                              <span
                                className={cn(
                                  'px-2 py-0.5 text-xs font-semibold rounded-full border',
                                  sentimentColorMap[item.sentiment as keyof typeof sentimentColorMap],
                                )}
                              >
                                {item.sentiment.toUpperCase()}
                              </span>
                            )}
                            <span className="text-xs text-slate-500">{formatNewsDate(item.publishedAt)}</span>
                            <span className="text-xs text-slate-500">{item.source}</span>
                          </div>
                          <p className="text-sm font-semibold text-slate-800">{item.title}</p>
                          {item.summary && <p className="text-sm text-slate-600">{item.summary}</p>}
                          <a
                            className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:underline"
                            href={item.url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            View source
                            <ArrowRight className="h-3 w-3" />
                          </a>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-slate-500">No relevant headlines were retrieved for this analysis window.</p>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-green-600" />
                      Recent Price & Volume
                    </CardTitle>
                    <CardDescription>Last 10 sessions (latest first)</CardDescription>
                  </CardHeader>
                  <CardContent className="overflow-x-auto">
                    {recentHistory.length ? (
                      <table className="w-full text-sm">
                        <thead className="text-xs uppercase text-slate-500">
                          <tr className="text-left">
                            <th className="pb-2">Date</th>
                            <th className="pb-2">Close</th>
                            <th className="pb-2">High</th>
                            <th className="pb-2">Low</th>
                            <th className="pb-2">Volume</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {recentHistory.map((row: HistoricalCandle, index: number) => (
                            <tr key={index} className="text-slate-700">
                              <td className="py-2">{row.date}</td>
                              <td className="py-2">{row.close !== null && row.close !== undefined ? `$${row.close.toFixed(2)}` : '—'}</td>
                              <td className="py-2">{row.high !== null && row.high !== undefined ? `$${row.high.toFixed(2)}` : '—'}</td>
                              <td className="py-2">{row.low !== null && row.low !== undefined ? `$${row.low.toFixed(2)}` : '—'}</td>
                              <td className="py-2">{row.volume !== null && row.volume !== undefined ? formatNumber(row.volume, 0) : '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div className="flex items-center gap-3 rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                        <Info className="h-4 w-4 text-slate-500" />
                        <span>
                          No recent price candles were received. This usually happens when the Alpha Vantage daily endpoint hits its rate limit or the symbol is not supported. Please retry in a few minutes or provide an alternative data source.
                        </span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}
          </div>

          {showHistory && (
            <div className="lg:col-span-1">
              <div className="sticky top-6">
                <HistoryPanel onLoadHistoryItem={handleLoadHistory} onHistoryChange={() => setHistoryCount(HistoryService.getHistory().length)} className="shadow-lg" />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
