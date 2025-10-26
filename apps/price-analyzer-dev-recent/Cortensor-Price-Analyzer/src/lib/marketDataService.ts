import axios from 'axios';
import {
  AnalysisHorizon,
  AssetType,
  CatalystHighlight,
  FundamentalSnapshot,
  HistoricalCandle,
  MarketAnalysisContext,
  MarketSnapshot,
  TechnicalSummary,
} from './marketTypes';

interface BuildContextParams {
  ticker: string;
  assetType: AssetType;
  horizon: AnalysisHorizon;
}

const HORIZON_DAYS: Record<AnalysisHorizon, number> = {
  '1W': 7,
  '1M': 30,
  '3M': 90,
  '6M': 180,
  '1Y': 365,
};

const COINGECKO_PRO_BASE_URL = 'https://pro-api.coingecko.com/api/v3';
const COINGECKO_DEMO_BASE_URL = 'https://api.coingecko.com/api/v3';
const STOOQ_DAILY_URL = 'https://stooq.com/q/d/l/';
const STOOQ_ALT_DAILY_URL = 'https://stooq.com/q/l/';
const TWELVEDATA_BASE_URL = 'https://api.twelvedata.com';
const TWELVEDATA_COMMODITY_MAP: Record<string, string> = {
  GC: 'XAU/USD',
  SI: 'SI',
  HG: 'HG',
  CL: 'CL',
  NG: 'NG',
  PL: 'XPT/USD',
  PA: 'XPD/USD',
  ZC: 'ZC',
  ZS: 'ZS',
  ZW: 'ZW',
  KC: 'KC',
  SB: 'SB',
  CC: 'CC',
  CT: 'CT',
};
const STOOQ_COMMODITY_MAP: Record<string, string[]> = {
  GC: ['gc.f'],
  SI: ['si.f'],
  HG: ['hg.f'],
  CL: ['cl.f'],
  NG: ['ng.f'],
  PL: ['pl.f'],
  PA: ['pa.f'],
  ZC: ['zc.f'],
  ZS: ['zs.f'],
  ZW: ['zw.f'],
  KC: ['kc.f'],
  SB: ['sb.f'],
  CC: ['cc.f'],
  CT: ['ct.f'],
};

type AlphaOverviewData = {
  snapshot: Partial<MarketSnapshot>;
  fundamentals: Partial<FundamentalSnapshot>;
};

const COIN_ALIAS_MAP: Record<string, string> = {
  BTC: 'bitcoin',
  XBT: 'bitcoin',
  BITCOIN: 'bitcoin',
  BCH: 'bitcoin-cash',
  BITCOINCASH: 'bitcoin-cash',
  ETH: 'ethereum',
  ETHEREUM: 'ethereum',
  ETC: 'ethereum-classic',
  ETHEREUMCLASSIC: 'ethereum-classic',
  SOL: 'solana',
  SOLANA: 'solana',
  ADA: 'cardano',
  CARDANO: 'cardano',
  XRP: 'ripple',
  RIPPLE: 'ripple',
  DOGE: 'dogecoin',
  DOGECOIN: 'dogecoin',
  DOT: 'polkadot',
  POLKADOT: 'polkadot',
  BNB: 'binancecoin',
  MATIC: 'matic-network',
  POLYGON: 'matic-network',
  LINK: 'chainlink',
  CHAINLINK: 'chainlink',
  LTC: 'litecoin',
  LITECOIN: 'litecoin',
  SHIB: 'shiba-inu',
  SHIBAINU: 'shiba-inu',
  AVAX: 'avalanche-2',
  AVALANCHE: 'avalanche-2',
  UNI: 'uniswap',
  UNISWAP: 'uniswap',
  ATOM: 'cosmos',
  COSMOS: 'cosmos',
  NEAR: 'near',
  ALGO: 'algorand',
  ALGORAND: 'algorand',
  TRX: 'tron',
  TRON: 'tron',
  APT: 'aptos',
  APTOS: 'aptos',
  ARB: 'arbitrum',
  ARBITRUM: 'arbitrum',
  OP: 'optimism',
  OPTIMISM: 'optimism',
  SUI: 'sui',
  TIA: 'celestia',
  CELESTIA: 'celestia',
  USDT: 'tether',
  TETHER: 'tether',
  USDC: 'usd-coin',
  USDCOIN: 'usd-coin',
  DAI: 'dai',
  BUSD: 'binance-usd',
  STETH: 'staked-ether',
  WBTC: 'wrapped-bitcoin',
};

export class MarketDataService {
  private alphaKey = process.env.ALPHA_VANTAGE_API_KEY;
  private finnhubKey = process.env.FINNHUB_API_KEY;
  private fmpKey = process.env.FMP_API_KEY;
  private coingeckoKey = process.env.COINGECKO_API_KEY;
  private coingeckoMode: 'pro' | 'demo' = process.env.COINGECKO_API_MODE === 'pro' ? 'pro' : 'demo';
  private coinIdCache = new Map<string, string | null>();
  private alphaOverviewCache = new Map<string, AlphaOverviewData | null>();
  private alphaOverviewInFlight = new Map<string, Promise<AlphaOverviewData | null>>();
  private twelvedataKey = process.env.TWELVEDATA_API_KEY ?? process.env.API;

  private async coingeckoGet<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    const isPro = this.coingeckoMode === 'pro';
    const baseUrl = isPro ? COINGECKO_PRO_BASE_URL : COINGECKO_DEMO_BASE_URL;
    const headers: Record<string, string> = {};
    const queryParams: Record<string, unknown> = { ...(params ?? {}) };

    if (this.coingeckoKey) {
      if (isPro) {
        headers['x-cg-pro-api-key'] = this.coingeckoKey;
      } else {
        headers['x-cg-demo-api-key'] = this.coingeckoKey;
      }
    } else if (!isPro) {
      // Allow attaching demo key via query string when present in env via COINGECKO_DEMO_API_KEY
      const demoQueryKey = process.env.COINGECKO_DEMO_API_KEY;
      if (demoQueryKey) {
        queryParams.x_cg_demo_api_key = demoQueryKey;
      }
    }

    const response = await axios.get<T>(`${baseUrl}${path}`, {
      params: queryParams,
      headers: Object.keys(headers).length > 0 ? headers : undefined,
    });

    return response.data;
  }

  async buildContext(params: BuildContextParams): Promise<MarketAnalysisContext> {
    const normalizedTicker = params.ticker.trim().toUpperCase();

    const [snapshot, history, fundamentals] = await Promise.all([
      this.fetchSnapshot(normalizedTicker, params.assetType),
      this.fetchHistory(normalizedTicker, params.assetType, params.horizon),
      this.fetchFundamentals(normalizedTicker, params.assetType),
    ]);

  const enhancedSnapshot = this.enrichSnapshotWithHistory(snapshot, history, params.assetType, normalizedTicker);

  const technicals = this.computeTechnicals(history);
    const catalysts = this.deriveCatalysts(snapshot, fundamentals, technicals);

    return {
      snapshot: { ...enhancedSnapshot, ticker: normalizedTicker, assetType: params.assetType },
      horizon: params.horizon,
      technicals,
      fundamentals,
      history,
      news: [],
      catalysts,
    };
  }

  private async fetchSnapshot(ticker: string, assetType: AssetType): Promise<MarketSnapshot> {
    const base: MarketSnapshot = {
      ticker,
      assetType,
    } as MarketSnapshot;

    if (assetType === 'crypto') {
      const cryptoSnapshot = await this.fetchCryptoSnapshot(ticker);
      return { ...base, ...cryptoSnapshot };
    }

    const [finnhub, fmpProfile, alphaQuote, alphaOverview] = await Promise.all([
      this.fetchFinnhubQuote(ticker),
      this.fetchFMPProfile(ticker),
      this.fetchAlphaGlobalQuote(ticker),
      this.fetchAlphaOverview(ticker),
    ]);

    const snapshot: MarketSnapshot = { ...base };
    const merge = (source?: Partial<MarketSnapshot> | null) => {
      if (!source) {
        return;
      }
      const filtered = Object.fromEntries(
        Object.entries(source).filter(([, value]) => value !== undefined && value !== null),
      );
      Object.assign(snapshot, filtered);
    };

    merge(alphaOverview?.snapshot);
    merge(fmpProfile);
    merge(finnhub);
    merge(alphaQuote);

    return snapshot;
  }

  private async fetchHistory(ticker: string, assetType: AssetType, horizon: AnalysisHorizon): Promise<HistoricalCandle[]> {
    if (assetType === 'crypto') {
      const cryptoHistory = await this.fetchCryptoHistory(ticker, horizon);
      if (cryptoHistory.length > 0) {
        return cryptoHistory;
      }
    }

    let alphaCandles: HistoricalCandle[] = [];

    if (this.alphaKey) {
      try {
        const functionName = this.getAlphaFunction(assetType);
        const params: Record<string, string> = {
          function: functionName,
          symbol: ticker,
          apikey: this.alphaKey,
        };

        if (assetType === 'crypto') {
          params.market = 'USD';
        }

        if (assetType === 'forex') {
          const [from, to] = ticker.split('/');
          if (from && to) {
            params.from_symbol = from;
            params.to_symbol = to;
            delete params.symbol;
          }
        }

        const response = await axios.get('https://www.alphavantage.co/query', { params });
        const data = response.data;

        const timeSeriesKey = Object.keys(data).find((key) => key.includes('Time Series'));
        if (timeSeriesKey) {
          const series = data[timeSeriesKey] as Record<string, Record<string, string>>;
          alphaCandles = Object.entries(series).map(([date, values]) => {
            const closeKey = Object.keys(values).find((key) => key.includes('close')) as string | undefined;
            const openKey = Object.keys(values).find((key) => key.includes('open')) as string | undefined;
            const highKey = Object.keys(values).find((key) => key.includes('high')) as string | undefined;
            const lowKey = Object.keys(values).find((key) => key.includes('low')) as string | undefined;
            const volumeKey = Object.keys(values).find((key) => key.includes('volume')) as string | undefined;

            const parseValue = (key?: string): number | null => {
              if (!key) {
                return null;
              }
              const raw = values[key];
              if (raw === undefined || raw === null) {
                return null;
              }
              const num = Number(raw);
              return Number.isFinite(num) ? num : null;
            };

            return {
              date,
              open: parseValue(openKey),
              high: parseValue(highKey),
              low: parseValue(lowKey),
              close: parseValue(closeKey),
              volume: parseValue(volumeKey),
            };
          });
        }
      } catch (error) {
        console.error('Alpha Vantage history fetch error:', error);
      }
    } else if (assetType === 'equity' || assetType === 'etf' || assetType === 'commodity') {
      console.warn('Alpha Vantage history unavailable (missing API key); will attempt Stooq fallback.');
    }

    const normalizedAlpha = this.normalizeHistoryRange(alphaCandles, horizon);
    if (normalizedAlpha.length > 0) {
      return normalizedAlpha;
    }

    if (assetType === 'equity' || assetType === 'etf' || assetType === 'commodity') {
      const stooqHistory = await this.fetchStooqDailyHistory(ticker, assetType);
      const normalizedStooq = this.normalizeHistoryRange(stooqHistory, horizon);
      if (normalizedStooq.length > 0) {
        console.warn(`Using Stooq history fallback for ${ticker}`);
        return normalizedStooq;
      }
    }

    const twelveDataHistory = await this.fetchTwelveDataHistory(ticker, assetType, horizon);
    if (twelveDataHistory.length > 0) {
      console.warn(`Using TwelveData history fallback for ${ticker} (${assetType})`);
      return twelveDataHistory;
    }

    return [];
  }

  private async fetchFundamentals(ticker: string, assetType: AssetType): Promise<FundamentalSnapshot> {
    if (assetType === 'crypto') {
      return {};
    }

    const [fmpMetrics, fmpQuote, alphaOverview] = await Promise.all([
      this.fetchFMPKeyMetrics(ticker),
      this.fetchFMPQuote(ticker),
      this.fetchAlphaOverview(ticker),
    ]);

    const alphaFundamentals = alphaOverview?.fundamentals ?? {};

    return {
      marketCap: fmpQuote.marketCap ?? alphaFundamentals.marketCap,
      peRatio: fmpMetrics?.peRatio ?? fmpQuote.pe ?? alphaFundamentals.peRatio,
      pbRatio: fmpMetrics?.pbRatio ?? alphaFundamentals.pbRatio,
      dividendYield: fmpQuote.dividendYield ?? alphaFundamentals.dividendYield,
      revenueGrowth: fmpMetrics?.revenueGrowth ?? alphaFundamentals.revenueGrowth,
      grossMargin: fmpMetrics?.grossMargin ?? alphaFundamentals.grossMargin,
      operatingMargin: fmpMetrics?.operatingMargin ?? alphaFundamentals.operatingMargin,
      netMargin: fmpMetrics?.netMargin ?? alphaFundamentals.netMargin,
      eps: fmpQuote.eps ?? alphaFundamentals.eps,
      freeCashFlow: fmpMetrics?.freeCashFlowPerShare ?? alphaFundamentals.freeCashFlow,
    };
  }

  private computeTechnicals(history: HistoricalCandle[]): TechnicalSummary {
    const closes = history.map((c) => c.close).filter((value): value is number => typeof value === 'number');
    const volumes = history.map((c) => c.volume).filter((value): value is number => typeof value === 'number');

    if (closes.length === 0) {
      return {};
    }

    const sma20 = this.simpleMovingAverage(closes, 20);
    const sma50 = this.simpleMovingAverage(closes, 50);
    const sma200 = this.simpleMovingAverage(closes, 200);
    const ema20 = this.exponentialMovingAverage(closes, 20);
    const rsi14 = this.relativeStrengthIndex(closes, 14);
    const { macd, signal, histogram } = this.macd(closes);
    const volatility = this.annualizedVolatility(closes);
    const { supportLevel, resistanceLevel } = this.supportResistance(closes);
    const volumeTrend = this.volumeTrend(volumes);

    return {
      sma20,
      sma50,
      sma200,
      ema20,
      rsi14,
      macd,
      macdSignal: signal,
      macdHistogram: histogram,
      volatility,
      supportLevel,
      resistanceLevel,
      volumeTrend,
    };
  }

  private deriveCatalysts(
    snapshot: Partial<MarketSnapshot>,
    fundamentals: FundamentalSnapshot,
    technicals: TechnicalSummary,
  ): CatalystHighlight[] {
    const catalysts: CatalystHighlight[] = [];

    if (typeof snapshot.changePercent === 'number') {
      if (snapshot.changePercent > 3) {
        catalysts.push({
          label: 'Strong Upside Move',
          description: `Price advanced ${snapshot.changePercent.toFixed(2)}% in the latest session`,
          impact: 'medium',
        });
      }
      if (snapshot.changePercent < -3) {
        catalysts.push({
          label: 'Sharp Drawdown',
          description: `Price declined ${snapshot.changePercent.toFixed(2)}% in the latest session`,
          impact: 'medium',
        });
      }
    }

    if (technicals.rsi14) {
      if (technicals.rsi14 > 70) {
        catalysts.push({
          label: 'Overbought RSI',
          description: `RSI at ${technicals.rsi14.toFixed(1)} signals elevated momentum`,
          impact: 'low',
        });
      }
      if (technicals.rsi14 < 30) {
        catalysts.push({
          label: 'Oversold RSI',
          description: `RSI at ${technicals.rsi14.toFixed(1)} may invite mean reversion`,
          impact: 'low',
        });
      }
    }

    if (fundamentals.peRatio && fundamentals.peRatio > 0 && fundamentals.peRatio > 35) {
      catalysts.push({
        label: 'Premium Valuation',
        description: `P/E ratio at ${fundamentals.peRatio.toFixed(1)} exceeds typical market multiples`,
        impact: 'medium',
      });
    }

    if (fundamentals.dividendYield && fundamentals.dividendYield > 0.04) {
      catalysts.push({
        label: 'High Dividend Yield',
        description: `Forward dividend yield around ${(fundamentals.dividendYield * 100).toFixed(2)}%`,
        impact: 'low',
      });
    }

    return catalysts.slice(0, 6);
  }

  private simpleMovingAverage(values: number[], period: number): number | undefined {
    if (values.length < period) return undefined;
    const slice = values.slice(-period);
    const sum = slice.reduce((acc, value) => acc + value, 0);
    return sum / period;
  }

  private exponentialMovingAverage(values: number[], period: number): number | undefined {
    if (values.length < period) return undefined;
    const k = 2 / (period + 1);
    let ema = this.simpleMovingAverage(values.slice(0, period), period);

    if (ema === undefined) {
      return undefined;
    }

    for (let i = period; i < values.length; i += 1) {
      ema = values[i] * k + (ema as number) * (1 - k);
    }

    return ema ?? undefined;
  }

  private relativeStrengthIndex(values: number[], period: number): number | undefined {
    if (values.length <= period) return undefined;

    let gains = 0;
    let losses = 0;

    for (let i = 1; i <= period; i += 1) {
      const change = values[i] - values[i - 1];
      if (change > 0) gains += change;
      else losses -= change;
    }

    let avgGain = gains / period;
    let avgLoss = losses / period;

    for (let i = period + 1; i < values.length; i += 1) {
      const change = values[i] - values[i - 1];
      if (change > 0) {
        avgGain = (avgGain * (period - 1) + change) / period;
        avgLoss = (avgLoss * (period - 1)) / period;
      } else {
        avgGain = (avgGain * (period - 1)) / period;
        avgLoss = (avgLoss * (period - 1) - change) / period;
      }
    }

    if (avgLoss === 0) return 100;
    if (avgGain === 0) return 0;

    const rs = avgGain / avgLoss;
    return 100 - 100 / (1 + rs);
  }

  private macd(values: number[]): { macd?: number; signal?: number; histogram?: number } {
    if (values.length < 35) return {};
    const ema12 = this.exponentialMovingAverage(values, 12);
    const ema26 = this.exponentialMovingAverage(values, 26);
    if (ema12 === undefined || ema26 === undefined) return {};
    const macd = ema12 - ema26;

    const macdSeries: number[] = [];
    const k12 = 2 / (12 + 1);
    const k26 = 2 / (26 + 1);
    let ema12Prev = values[0];
    let ema26Prev = values[0];

    values.forEach((price) => {
      ema12Prev = price * k12 + ema12Prev * (1 - k12);
      ema26Prev = price * k26 + ema26Prev * (1 - k26);
      macdSeries.push(ema12Prev - ema26Prev);
    });

    const signal = this.exponentialMovingAverage(macdSeries, 9);
    if (signal === undefined) return { macd };
    const histogram = macd - signal;
    return { macd, signal, histogram };
  }

  private annualizedVolatility(values: number[]): number | undefined {
    if (values.length < 10) return undefined;
    const returns: number[] = [];
    for (let i = 1; i < values.length; i += 1) {
      const prev = values[i - 1];
      const curr = values[i];
      if (prev > 0) {
        returns.push(Math.log(curr / prev));
      }
    }

    if (returns.length === 0) return undefined;
    const mean = returns.reduce((acc, value) => acc + value, 0) / returns.length;
    const variance = returns.reduce((acc, value) => acc + (value - mean) ** 2, 0) / (returns.length - 1 || 1);
    const dailyVol = Math.sqrt(variance);
    return dailyVol * Math.sqrt(252);
  }

  private supportResistance(values: number[]): { supportLevel?: number; resistanceLevel?: number } {
    if (values.length === 0) return {};
    const recent = values.slice(-30);
    return {
      supportLevel: Math.min(...recent),
      resistanceLevel: Math.max(...recent),
    };
  }

  private volumeTrend(volumes: number[]): number | undefined {
    if (volumes.length < 20) return undefined;
    const short = this.simpleMovingAverage(volumes, 5);
    const long = this.simpleMovingAverage(volumes, 20);
    if (!short || !long || long === 0) return undefined;
    return short / long;
  }

  private getAlphaFunction(assetType: AssetType): string {
    switch (assetType) {
      case 'crypto':
        return 'DIGITAL_CURRENCY_DAILY';
      case 'forex':
        return 'FX_DAILY';
      default:
        return 'TIME_SERIES_DAILY_ADJUSTED';
    }
  }

  private async fetchFinnhubQuote(ticker: string): Promise<Partial<MarketSnapshot>> {
    if (!this.finnhubKey) return {};
    try {
      const [quoteResponse, profileResponse] = await Promise.all([
        axios.get('https://finnhub.io/api/v1/quote', {
          params: { symbol: ticker, token: this.finnhubKey },
        }),
        axios.get('https://finnhub.io/api/v1/stock/profile2', {
          params: { symbol: ticker, token: this.finnhubKey },
        }),
      ]);

      const quote = quoteResponse.data as Record<string, unknown>;
      const profile = profileResponse.data as Record<string, unknown>;

      return {
        latestPrice: this.safeNumber(quote.c),
        open: this.safeNumber(quote.o),
        high: this.safeNumber(quote.h),
        low: this.safeNumber(quote.l),
        previousClose: this.safeNumber(quote.pc),
        change: this.safeNumber(quote.d),
        changePercent: this.safeNumber(quote.dp),
        volume: this.safeNumber(quote.v),
        companyName: typeof profile.name === 'string' ? profile.name : undefined,
        exchange: typeof profile.exchange === 'string' ? profile.exchange : undefined,
        currency: typeof profile.currency === 'string' ? profile.currency : 'USD',
        sector: typeof profile.finnhubIndustry === 'string' ? profile.finnhubIndustry : undefined,
        country: typeof profile.country === 'string' ? profile.country : undefined,
        beta: this.safeNumber(profile.beta),
        lastUpdated: new Date().toISOString(),
      };
    } catch (error) {
      console.error('Finnhub snapshot error:', error);
      return {};
    }
  }

  private async fetchFMPProfile(ticker: string): Promise<Partial<MarketSnapshot>> {
    if (!this.fmpKey) return {};
    try {
      const response = await axios.get(`https://financialmodelingprep.com/api/v3/profile/${ticker}`, {
        params: { apikey: this.fmpKey },
      });
      const data = Array.isArray(response.data) ? response.data[0] : undefined;
      if (!data) return {};

      return {
        companyName: data.companyName || data.name,
        exchange: data.exchangeShortName || data.exchange,
        currency: data.currency || data.defaultCurrency || 'USD',
        industry: data.industry,
        sector: data.sector,
        averageVolume: this.safeNumber(data.volAvg),
        lastUpdated: data.lastDivDate || data.lastUpdated || new Date().toISOString(),
      };
    } catch (error) {
      console.error('FMP profile error:', error);
      return {};
    }
  }

  private async fetchFMPQuote(ticker: string): Promise<{ marketCap?: number; pe?: number; dividendYield?: number; eps?: number }> {
    if (!this.fmpKey) return {};
    try {
      const response = await axios.get(`https://financialmodelingprep.com/api/v3/quote/${ticker}`, {
        params: { apikey: this.fmpKey },
      });
      const data = Array.isArray(response.data) ? response.data[0] : undefined;
      if (!data) return {};

      return {
        marketCap: this.safeNumber(data.marketCap),
        pe: this.safeNumber(data.pe),
        dividendYield: this.safeNumber(data.dividendYield),
        eps: this.safeNumber(data.eps),
      };
    } catch (error) {
      console.error('FMP quote error:', error);
      return {};
    }
  }

  private async fetchAlphaGlobalQuote(ticker: string): Promise<Partial<MarketSnapshot>> {
    if (!this.alphaKey) {
      return {};
    }

    try {
      const response = await axios.get('https://www.alphavantage.co/query', {
        params: {
          function: 'GLOBAL_QUOTE',
          symbol: ticker,
          apikey: this.alphaKey,
        },
      });

      const data = response.data?.['Global Quote'];
      if (!data || typeof data !== 'object') {
        return {};
      }

      const parsePercent = (value: unknown): number | undefined => {
        if (typeof value !== 'string') {
          return undefined;
        }
        return this.safeNumber(value.replace('%', ''));
      };

      const latestTradingDay = typeof data['07. latest trading day'] === 'string' ? data['07. latest trading day'] : undefined;

      return {
        latestPrice: this.safeNumber((data as Record<string, unknown>)['05. price']),
        open: this.safeNumber((data as Record<string, unknown>)['02. open']),
        high: this.safeNumber((data as Record<string, unknown>)['03. high']),
        low: this.safeNumber((data as Record<string, unknown>)['04. low']),
        previousClose: this.safeNumber((data as Record<string, unknown>)['08. previous close']),
        change: this.safeNumber((data as Record<string, unknown>)['09. change']),
        changePercent: parsePercent((data as Record<string, unknown>)['10. change percent']),
        volume: this.safeNumber((data as Record<string, unknown>)['06. volume']),
        lastUpdated: latestTradingDay ? `${latestTradingDay}T00:00:00Z` : undefined,
      };
    } catch (error) {
      console.warn('Alpha Vantage global quote error:', error);
      return {};
    }
  }

  private async fetchAlphaOverview(ticker: string): Promise<AlphaOverviewData | null> {
    if (!this.alphaKey) {
      return null;
    }

    const cacheKey = ticker.trim().toUpperCase();
    if (this.alphaOverviewCache.has(cacheKey)) {
      return this.alphaOverviewCache.get(cacheKey) ?? null;
    }

    if (this.alphaOverviewInFlight.has(cacheKey)) {
      return this.alphaOverviewInFlight.get(cacheKey) ?? null;
    }

    const request = (async () => {
      try {
        const response = await axios.get('https://www.alphavantage.co/query', {
          params: {
            function: 'OVERVIEW',
            symbol: ticker,
            apikey: this.alphaKey,
          },
        });

        const data = response.data as Record<string, unknown> | undefined;
        if (!data || typeof data.Symbol !== 'string') {
          this.alphaOverviewCache.set(cacheKey, null);
          return null;
        }

        const snapshot: Partial<MarketSnapshot> = {
          companyName: typeof data.Name === 'string' ? data.Name : undefined,
          exchange: typeof data.Exchange === 'string' ? data.Exchange : undefined,
          currency: typeof data.Currency === 'string' ? data.Currency : undefined,
          sector: typeof data.Sector === 'string' ? data.Sector : undefined,
          industry: typeof data.Industry === 'string' ? data.Industry : undefined,
          country: typeof data.Country === 'string' ? data.Country : undefined,
          beta: this.safeNumber(data.Beta),
          lastUpdated: new Date().toISOString(),
        };

        const fundamentals: Partial<FundamentalSnapshot> = {
          marketCap: this.safeNumber(data.MarketCapitalization),
          peRatio: this.safeNumber(data.PERatio),
          pbRatio: this.safeNumber(data.PriceToBookRatio),
          dividendYield: this.safeNumber(data.DividendYield),
          revenueGrowth: this.safeNumber(data.QuarterlyRevenueGrowthYOY),
          grossMargin: this.safeNumber(data.GrossMarginTTM),
          operatingMargin: this.safeNumber(data.OperatingMarginTTM),
          netMargin: this.safeNumber(data.ProfitMargin),
          eps: this.safeNumber(data.EPS),
        };

        const freeCashFlow = this.safeNumber(data.FreeCashFlowTTM);
        const sharesOutstanding = this.safeNumber(data.SharesOutstanding);
        if (freeCashFlow !== undefined && sharesOutstanding) {
          fundamentals.freeCashFlow = sharesOutstanding !== 0 ? freeCashFlow / sharesOutstanding : undefined;
        }

        const overview: AlphaOverviewData = { snapshot, fundamentals };
        this.alphaOverviewCache.set(cacheKey, overview);
        return overview;
      } catch (error) {
        console.warn('Alpha Vantage overview error:', error);
        this.alphaOverviewCache.set(cacheKey, null);
        return null;
      } finally {
        this.alphaOverviewInFlight.delete(cacheKey);
      }
    })();

    this.alphaOverviewInFlight.set(cacheKey, request);
    return request;
  }

  private async fetchFMPKeyMetrics(ticker: string): Promise<{
    peRatio?: number;
    pbRatio?: number;
    revenueGrowth?: number;
    grossMargin?: number;
    operatingMargin?: number;
    netMargin?: number;
    freeCashFlowPerShare?: number;
  } | null> {
    if (!this.fmpKey) return null;
    try {
      const response = await axios.get(`https://financialmodelingprep.com/api/v3/key-metrics-ttm/${ticker}`, {
        params: { apikey: this.fmpKey },
      });
      const data = Array.isArray(response.data) ? response.data[0] : undefined;
      if (!data) return null;

      return {
        peRatio: this.safeNumber(data.peRatioTTM),
        pbRatio: this.safeNumber(data.priceToBookRatioTTM),
        revenueGrowth: this.safeNumber(data.revenuePerShareTTMGrowth),
        grossMargin: this.safeNumber(data.grossProfitMarginTTM),
        operatingMargin: this.safeNumber(data.operatingProfitMarginTTM),
        netMargin: this.safeNumber(data.netIncomeMarginTTM),
        freeCashFlowPerShare: this.safeNumber(data.freeCashFlowPerShareTTM),
      };
    } catch (error) {
      console.error('FMP key metrics error:', error);
      return null;
    }
  }

  private async fetchCryptoSnapshot(ticker: string): Promise<Partial<MarketSnapshot>> {
    try {
      const id = await this.resolveCoinId(ticker);
      if (!id) {
        console.warn(`Coingecko snapshot skipped: unable to resolve coin id for ${ticker}`);
        return {};
      }
      const data = await this.coingeckoGet<{
        name?: string;
        market_data?: {
          current_price?: { usd?: number };
          price_change_percentage_24h?: number;
          price_change_24h?: number;
          high_24h?: { usd?: number };
          low_24h?: { usd?: number };
          market_cap?: { usd?: number };
          total_volume?: { usd?: number };
          last_updated?: string;
        };
      }>(`/coins/${id}`,
        {
          localization: 'false',
          tickers: 'false',
          market_data: 'true',
          community_data: 'false',
          developer_data: 'false',
          sparkline: 'false',
        },
      );

      const marketData = data?.market_data;
      if (!marketData) return {};

      return {
        companyName: data?.name,
        currency: 'USD',
        latestPrice: this.safeNumber(marketData.current_price?.usd),
        changePercent: this.safeNumber(marketData.price_change_percentage_24h),
        change: this.safeNumber(marketData.price_change_24h),
        high: this.safeNumber(marketData.high_24h?.usd),
        low: this.safeNumber(marketData.low_24h?.usd),
        marketCap: this.safeNumber(marketData.market_cap?.usd),
        volume: this.safeNumber(marketData.total_volume?.usd),
        lastUpdated: marketData.last_updated,
      } as Partial<MarketSnapshot>;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status;
        const message = (error.response?.data as { error?: string } | undefined)?.error ?? error.message;
        console.warn(`Coingecko snapshot error (${ticker}): ${status ?? 'unknown'} ${message}`);
      } else {
        console.warn(`Coingecko snapshot error (${ticker}):`, error);
      }
      return {};
    }
  }

  private async fetchCryptoHistory(ticker: string, horizon: AnalysisHorizon): Promise<HistoricalCandle[]> {
    try {
      const id = await this.resolveCoinId(ticker);
      if (!id) {
        console.warn(`Coingecko history skipped: unable to resolve coin id for ${ticker}`);
        return [];
      }
      const days = HORIZON_DAYS[horizon];
      const data = await this.coingeckoGet<{
        prices?: [number, number][];
        total_volumes?: [number, number][];
      }>(`/coins/${id}/market_chart`, {
        vs_currency: 'usd',
        days,
        interval: days <= 7 ? 'hourly' : 'daily',
      });

      const prices: [number, number][] = data?.prices || [];
      const volumes: [number, number][] = data?.total_volumes || [];

      if (!prices.length) return [];

      return prices.map(([timestamp, price], index) => {
        const volume = volumes[index]?.[1] ?? null;
        const date = new Date(timestamp).toISOString().split('T')[0];
        return {
          date,
          open: price,
          high: price,
          low: price,
          close: price,
          volume,
        };
      });
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status;
        const message = (error.response?.data as { error?: string } | undefined)?.error ?? error.message;
        console.warn(`Coingecko history error (${ticker}): ${status ?? 'unknown'} ${message}`);
      } else {
        console.warn(`Coingecko history error (${ticker}):`, error);
      }
      return [];
    }
  }

  private async resolveCoinId(ticker: string): Promise<string | null> {
    const normalized = ticker.trim().toUpperCase();
    if (!normalized) {
      return null;
    }

    const sanitized = normalized.replace(/[^A-Z0-9]/g, '');
    const cacheKey = sanitized || normalized;

    if (this.coinIdCache.has(cacheKey)) {
      return this.coinIdCache.get(cacheKey) ?? null;
    }

    const aliasMatch = COIN_ALIAS_MAP[normalized] ?? COIN_ALIAS_MAP[sanitized];
    if (aliasMatch) {
      this.coinIdCache.set(cacheKey, aliasMatch);
      return aliasMatch;
    }

    try {
      const data = await this.coingeckoGet<{ coins?: Array<{ id?: string; symbol?: string; name?: string }> }>(
        '/search',
        { query: normalized },
      );

      const coins = Array.isArray(data?.coins) ? data.coins : [];
      const lowerSanitized = sanitized.toLowerCase();

      const exactSymbolMatch = coins.find((coin) => {
        const coinSymbol = coin.symbol?.replace(/[^A-Za-z0-9]/g, '').toLowerCase();
        return coinSymbol === lowerSanitized && typeof coin.id === 'string';
      });

      if (exactSymbolMatch?.id) {
        this.coinIdCache.set(cacheKey, exactSymbolMatch.id);
        return exactSymbolMatch.id;
      }

      const exactNameMatch = coins.find((coin) => {
        const coinName = coin.name?.replace(/[^A-Za-z0-9]/g, '').toLowerCase();
        return coinName === lowerSanitized && typeof coin.id === 'string';
      });

      if (exactNameMatch?.id) {
        this.coinIdCache.set(cacheKey, exactNameMatch.id);
        return exactNameMatch.id;
      }

      const topResult = coins.find((coin) => typeof coin.id === 'string')?.id ?? null;
      if (topResult) {
        this.coinIdCache.set(cacheKey, topResult);
        return topResult;
      }
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status;
        const message = (error.response?.data as { error?: string } | undefined)?.error ?? error.message;
        console.warn(`Coingecko symbol resolution error (${normalized}): ${status ?? 'unknown'} ${message}`);
      } else {
        console.warn(`Coingecko symbol resolution error (${normalized}):`, error);
      }
    }

    this.coinIdCache.set(cacheKey, null);
    return null;
  }

  private normalizeHistoryRange(candles: HistoricalCandle[], horizon: AnalysisHorizon): HistoricalCandle[] {
    if (!candles.length) {
      return [];
    }

    const normalized = candles
      .filter((candle) => {
        if (!candle.date) return false;
        const timestamp = new Date(candle.date).getTime();
        return Number.isFinite(timestamp);
      })
      .map((candle) => {
        const isoDate = new Date(candle.date).toISOString().split('T')[0];
        return { ...candle, date: isoDate };
      })
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    if (!normalized.length) {
      return [];
    }

    const days = HORIZON_DAYS[horizon];
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days * 1.4);

    return normalized
      .filter((candle) => new Date(candle.date).getTime() >= cutoff.getTime())
      .slice(-days * 3);
  }

  private getStooqSymbols(ticker: string, assetType: AssetType): string[] {
    const normalized = ticker.trim().toLowerCase();
    if (!normalized) {
      return [];
    }

    if (assetType === 'commodity') {
      const root = normalized.replace(/([=:\-].*)$/, '');
      const upperRoot = root.toUpperCase();
      const candidates = new Set<string>();

      const mapped = STOOQ_COMMODITY_MAP[upperRoot];
      if (mapped) {
        mapped.forEach((symbol) => candidates.add(symbol.toLowerCase()));
      }

      if (root) {
        candidates.add(`${root}.f`);
        candidates.add(root);
      }

      return Array.from(candidates);
    }

    if (assetType === 'equity' || assetType === 'etf') {
      const candidates = new Set<string>();

      if (normalized.includes('.')) {
        candidates.add(normalized);
      } else {
        candidates.add(`${normalized}.us`);
        candidates.add(normalized);
      }

      return Array.from(candidates);
    }

    return [];
  }

  private async fetchStooqDailyHistory(ticker: string, assetType: AssetType): Promise<HistoricalCandle[]> {
    const symbols = this.getStooqSymbols(ticker, assetType);
    if (!symbols.length) {
      return [];
    }

    const parseNumber = (value: string): number | null => {
      const clean = value.trim();
      if (!clean || clean === '-' || clean.toLowerCase() === 'nan') {
        return null;
      }
      const num = Number(clean);
      return Number.isFinite(num) ? num : null;
    };

    for (const symbol of symbols) {
      const requests = assetType === 'commodity'
        ? [
            { url: STOOQ_DAILY_URL, params: { s: symbol, i: 'd' } },
            { url: STOOQ_ALT_DAILY_URL, params: { s: symbol, f: 'sd2t2ohlcv', e: 'csv', h: '' } },
          ]
        : [
            { url: STOOQ_DAILY_URL, params: { s: symbol, i: 'd' } },
          ];

      for (const request of requests) {
        try {
          const response = await axios.get<string>(request.url, {
            params: request.params,
            responseType: 'text',
          });

          const csv = typeof response.data === 'string' ? response.data : '';
          const trimmed = csv.trim();
          if (!trimmed || trimmed.toLowerCase() === 'no data') {
            continue;
          }

          const lines = trimmed.split(/\r?\n/);
          if (lines.length <= 1 || lines[0].toLowerCase().startsWith('error')) {
            continue;
          }

          const rows = lines.slice(1).filter((line) => line.trim().length > 0);
          const candles = rows
            .map((line) => line.split(',').map((part) => part.trim()))
            .filter((parts) => parts.length >= 6)
            .map((parts) => {
              const [date, open, high, low, close, volume] = parts;
              return {
                date,
                open: parseNumber(open),
                high: parseNumber(high),
                low: parseNumber(low),
                close: parseNumber(close),
                volume: parseNumber(volume),
              } as HistoricalCandle;
            });

          if (candles.length) {
            return candles;
          }
        } catch (error) {
          console.warn(`Stooq history error (${symbol} via ${request.url}):`, error);
        }
      }
    }

    return [];
  }

  private getTwelveDataSymbol(ticker: string, assetType: AssetType): string | null {
    const cleaned = ticker.trim().toUpperCase();
    if (!cleaned) {
      return null;
    }

    if (assetType === 'crypto') {
      if (cleaned.includes('/')) {
        return cleaned;
      }
      return `${cleaned}/USD`;
    }

    if (assetType === 'forex') {
      return cleaned.includes('/') ? cleaned : `${cleaned}/USD`;
    }

    if (assetType === 'commodity') {
      const root = cleaned.replace(/([=:\-].*)$/, '');
      const mapped = TWELVEDATA_COMMODITY_MAP[root];
      if (mapped) {
        return mapped;
      }
      if (root) {
        return root;
      }
      return cleaned;
    }

    return cleaned;
  }

  private async fetchTwelveDataHistory(ticker: string, assetType: AssetType, horizon: AnalysisHorizon): Promise<HistoricalCandle[]> {
    if (!this.twelvedataKey) {
      return [];
    }

    const symbol = this.getTwelveDataSymbol(ticker, assetType);
    if (!symbol) {
      return [];
    }

    try {
      const response = await axios.get(`${TWELVEDATA_BASE_URL}/time_series`, {
        params: {
          symbol,
          interval: '1day',
          outputsize: '5000',
          apikey: this.twelvedataKey,
        },
      });

      const data = response.data as { status?: string; values?: Array<Record<string, string>>; message?: string } | undefined;
      if (!data || data.status !== 'ok' || !Array.isArray(data.values)) {
        if (data?.status && data.status !== 'ok') {
          const message = data.message ?? 'Unknown TwelveData error';
          console.warn(`TwelveData history error (${ticker}): ${data.status} ${message}`);
        }
        return [];
      }

      const parseValue = (value: unknown): number | null => {
        if (typeof value !== 'string') {
          return null;
        }
        const num = Number(value);
        return Number.isFinite(num) ? num : null;
      };

      const candles: HistoricalCandle[] = data.values
        .map((entry) => ({
          date: entry.datetime,
          open: parseValue(entry.open),
          high: parseValue(entry.high),
          low: parseValue(entry.low),
          close: parseValue(entry.close),
          volume: parseValue(entry.volume),
        }))
        .filter((candle) => typeof candle.date === 'string');

      return this.normalizeHistoryRange(candles, horizon);
    } catch (error) {
      console.warn(`TwelveData history request failed (${ticker}):`, error);
      return [];
    }
  }

  private safeNumber(value: unknown): number | undefined {
    if (value === null || value === undefined) return undefined;
    const num = Number(value);
    return Number.isFinite(num) ? num : undefined;
  }

  private enrichSnapshotWithHistory(
    snapshot: MarketSnapshot,
    history: HistoricalCandle[],
    assetType: AssetType,
    ticker: string,
  ): MarketSnapshot {
    if (!history.length) {
      return snapshot;
    }

    const pricedCandles = history
      .filter((candle): candle is HistoricalCandle & { close: number } => typeof candle.close === 'number')
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    if (!pricedCandles.length) {
      return snapshot;
    }

    const latest = pricedCandles[pricedCandles.length - 1];
    const previous = pricedCandles.length > 1 ? pricedCandles[pricedCandles.length - 2] : undefined;

    const enriched: MarketSnapshot = { ...snapshot };
    const isInvalid = (value: number | null | undefined): boolean => {
      if (value === undefined || value === null) {
        return true;
      }
      if (typeof value !== 'number') {
        return true;
      }
      if (!Number.isFinite(value)) {
        return true;
      }
      return value <= 0;
    };

    if (isInvalid(enriched.latestPrice)) {
      enriched.latestPrice = latest.close;
    }

    if ((enriched.change === undefined || enriched.change === null || !Number.isFinite(enriched.change)) && previous) {
      enriched.change = latest.close - previous.close;
    }

    if ((enriched.changePercent === undefined || enriched.changePercent === null || !Number.isFinite(enriched.changePercent)) && previous && previous.close !== 0) {
      enriched.changePercent = ((latest.close - previous.close) / previous.close) * 100;
    }

    if (isInvalid(enriched.previousClose)) {
      enriched.previousClose = previous?.close ?? latest.close;
    }

    if (!enriched.currency) {
      enriched.currency = assetType === 'forex' ? currencyFromPair(ticker, enriched.currency) : 'USD';
    }

    if (!enriched.lastUpdated) {
      enriched.lastUpdated = new Date(latest.date).toISOString();
    }

    if (!enriched.volume && typeof latest.volume === 'number') {
      enriched.volume = latest.volume;
    }

    return enriched;

    function currencyFromPair(symbol: string, fallback?: string): string | undefined {
      if (!symbol.includes('/')) {
        return fallback;
      }
      const [, quote] = symbol.split('/');
      return quote || fallback;
    }
  }
}

export type { BuildContextParams };
