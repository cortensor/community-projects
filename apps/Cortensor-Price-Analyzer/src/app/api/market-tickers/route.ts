import { snapshotStore } from '@/lib/snapshotStore';
import axios from 'axios';
import { NextResponse } from 'next/server';

export type AssetKind = 'equity' | 'crypto' | 'forex' | 'commodity';
export type QuoteProvider = 'coingecko' | 'stooq' | 'twelvedata' | 'alphavantage' | 'marketstack' | 'massive';

type WatchItem = {
  symbol: string;
  name: string;
  type: AssetKind;
  currency?: string;
  providers?: Partial<Record<QuoteProvider, string>>;
};

export type MarketTickerItem = WatchItem & {
  price?: number;
  changePercent?: number;
};

type ProviderResult = {
  items: MarketTickerItem[];
  refreshedAt: string | null;
};

const EQUITY_WATCHLIST: WatchItem[] = [
  { symbol: 'NVDA', name: 'NVIDIA', type: 'equity', providers: { stooq: 'nvda.us', twelvedata: 'NVDA', massive: 'NVDA' } },
  { symbol: 'AAPL', name: 'Apple', type: 'equity', providers: { stooq: 'aapl.us', twelvedata: 'AAPL', massive: 'AAPL' } },
  { symbol: 'MSFT', name: 'Microsoft', type: 'equity', providers: { stooq: 'msft.us', twelvedata: 'MSFT', massive: 'MSFT' } },
  { symbol: 'TSLA', name: 'Tesla', type: 'equity', providers: { stooq: 'tsla.us', twelvedata: 'TSLA', massive: 'TSLA' } },
  { symbol: 'META', name: 'Meta Platforms', type: 'equity', providers: { stooq: 'meta.us', twelvedata: 'META', massive: 'META' } },
  { symbol: 'AMZN', name: 'Amazon', type: 'equity', providers: { stooq: 'amzn.us', twelvedata: 'AMZN', massive: 'AMZN' } },
];

const CRYPTO_WATCHLIST: WatchItem[] = [
  { symbol: 'BTCUSD', name: 'Bitcoin', type: 'crypto', providers: { coingecko: 'bitcoin', twelvedata: 'BTC/USD' } },
  { symbol: 'ETHUSD', name: 'Ethereum', type: 'crypto', providers: { coingecko: 'ethereum', twelvedata: 'ETH/USD' } },
  { symbol: 'SOLUSD', name: 'Solana', type: 'crypto', providers: { coingecko: 'solana', twelvedata: 'SOL/USD' } },
  { symbol: 'XRPUSD', name: 'XRP', type: 'crypto', providers: { coingecko: 'ripple', twelvedata: 'XRP/USD' } },
  { symbol: 'DOGEUSD', name: 'Dogecoin', type: 'crypto', providers: { coingecko: 'dogecoin', twelvedata: 'DOGE/USD' } },
];

const FOREX_WATCHLIST: WatchItem[] = [
  { symbol: 'EURUSD', name: 'Euro / US Dollar', type: 'forex', providers: { alphavantage: 'EURUSD', twelvedata: 'EUR/USD' } },
  { symbol: 'USDJPY', name: 'US Dollar / Japanese Yen', type: 'forex', providers: { alphavantage: 'USDJPY', twelvedata: 'USD/JPY' } },
  { symbol: 'GBPUSD', name: 'British Pound / US Dollar', type: 'forex', providers: { alphavantage: 'GBPUSD', twelvedata: 'GBP/USD' } },
  { symbol: 'AUDUSD', name: 'Australian Dollar / US Dollar', type: 'forex', providers: { alphavantage: 'AUDUSD', twelvedata: 'AUD/USD' } },
  { symbol: 'USDCAD', name: 'US Dollar / Canadian Dollar', type: 'forex', providers: { alphavantage: 'USDCAD', twelvedata: 'USD/CAD' } },
];

const COMMODITY_WATCHLIST: WatchItem[] = [
  {
    symbol: 'XAUUSD',
    name: 'Gold',
    type: 'commodity',
    providers: {
      alphavantage: 'XAUUSD',
      massive: 'product:GC',
      marketstack: 'XAUUSD',
      stooq: 'xauusd',
      twelvedata: 'XAU/USD',
    },
  },
  {
    symbol: 'XAGUSD',
    name: 'Silver',
    type: 'commodity',
    providers: {
      alphavantage: 'XAGUSD',
      massive: 'product:SI',
      marketstack: 'XAGUSD',
      stooq: 'xagusd',
      twelvedata: 'XAG/USD',
    },
  },
  {
    symbol: 'WTIUSD',
    name: 'Crude Oil WTI',
    type: 'commodity',
    providers: {
      alphavantage: 'WTI',
      massive: 'product:CL',
      marketstack: 'WTIUSD',
      stooq: 'cl.f',
      twelvedata: 'WTI/USD',
    },
  },
  {
    symbol: 'BRENTUSD',
    name: 'Crude Oil Brent',
    type: 'commodity',
    providers: {
      alphavantage: 'BRENT',
      stooq: 'brn.f',
    },
  },
  {
    symbol: 'NGUSD',
    name: 'Natural Gas',
    type: 'commodity',
    providers: {
      alphavantage: 'NATURAL_GAS',
      massive: 'product:NG',
      marketstack: 'NGUSD',
      stooq: 'ng.f',
      twelvedata: 'NG/USD',
    },
  },
];

const TWELVEDATA_BASE_URL = 'https://api.twelvedata.com';
const STOOQ_QUOTE_URL = 'https://stooq.com/q/l/';
const ALPHA_VANTAGE_BASE_URL = 'https://www.alphavantage.co/query';
const MARKETSTACK_BASE_URL = 'https://api.marketstack.com/v1';
const MASSIVE_BASE_URL = 'https://api.massive.com';
const COINGECKO_BASE_URL = 'https://api.coingecko.com/api/v3';

const twelvedataKey = process.env.TWELVEDATA_API_KEY;
const twelvedataCommodityKey = process.env.TWELVEDATA_COMMODITY_API_KEY ?? null;
const twelvedataStocksKey = process.env.TWELVEDATA_STOCKS_API_KEY ?? null;
const alphaVantagePrimaryKey = process.env.ALPHA_VANTAGE_API_KEY;
const alphaVantageForexKey = process.env.ALPHA_VANTAGE_FOREX_API_KEY ?? alphaVantagePrimaryKey;
const alphaVantageCommodityKey = alphaVantagePrimaryKey ?? alphaVantageForexKey;
const alphaVantageRetryKey = process.env.ALPHA_VANTAGE_RETRY_API_KEY ?? alphaVantagePrimaryKey;
const marketstackKey = process.env.MARKETSTACK_API_KEY;
const massiveKey = process.env.MASSIVE_API_KEY;
const coingeckoKey = process.env.COINGECKO_API_KEY;

type AlphaMacroCommodityFunction = 'WTI' | 'BRENT' | 'NATURAL_GAS';

type AlphaCommoditySpec =
  | { mode: 'dailySeries'; symbol: string }
  | { mode: 'macroSeries'; function: AlphaMacroCommodityFunction; interval: 'daily' | 'weekly' | 'monthly' };

const ALPHA_COMMODITY_SPECS: Record<string, AlphaCommoditySpec> = {
  XAUUSD: { mode: 'dailySeries', symbol: 'XAUUSD' },
  XAGUSD: { mode: 'dailySeries', symbol: 'XAGUSD' },
  WTIUSD: { mode: 'macroSeries', function: 'WTI', interval: 'daily' },
  BRENTUSD: { mode: 'macroSeries', function: 'BRENT', interval: 'daily' },
  NGUSD: { mode: 'macroSeries', function: 'NATURAL_GAS', interval: 'daily' },
};

export type WatchlistKey = 'equities' | 'crypto' | 'forex' | 'commodities';

type CategorySpec = {
  items: WatchItem[];
  providers: QuoteProvider[];
  ttlMs: number;
  requireComplete?: boolean;
};

const CATEGORY_SPECS: Record<WatchlistKey, CategorySpec> = {
  equities: { items: EQUITY_WATCHLIST, providers: ['twelvedata', 'stooq', 'marketstack', 'massive'], ttlMs: 5 * 60 * 1000 },
  crypto: { items: CRYPTO_WATCHLIST, providers: ['coingecko', 'twelvedata'], ttlMs: 10 * 60 * 1000 },
  forex: { items: FOREX_WATCHLIST, providers: ['twelvedata', 'alphavantage'], ttlMs: 60 * 60 * 1000 },
  commodities: {
    items: COMMODITY_WATCHLIST,
    // Prioritize twelvedata and stooq first (no strict rate limits), alphavantage as last fallback
    providers: ['twelvedata', 'stooq', 'alphavantage'],
    ttlMs: 15 * 60 * 1000,
    requireComplete: true,
  },
};

export type CategorySnapshot = {
  items: MarketTickerItem[];
  provider: QuoteProvider;
  refreshedAt: string | null;
  errors: string[];
};

export type CategoryMeta = {
  provider: QuoteProvider;
  ttlSeconds: number;
  lastUpdated: string | null;
  errors: string[];
};

const categoryCache: Partial<Record<WatchlistKey, { timestamp: number; snapshot: CategorySnapshot }>> = {};

export async function GET() {
  const keys = Object.keys(CATEGORY_SPECS) as WatchlistKey[];
  const snapshots = await Promise.all(keys.map((key) => getCategorySnapshot(key)));

  const data = keys.reduce(
    (acc, key, index) => {
      acc[key] = snapshots[index].items;
      return acc;
    },
    {} as Record<WatchlistKey, MarketTickerItem[]>
  );

  const refreshedAt = getLatestTimestamp(snapshots.map((snapshot) => snapshot.refreshedAt));

  const metaCategories = keys.reduce(
    (acc, key, index) => {
      const spec = CATEGORY_SPECS[key];
      acc[key] = {
        provider: snapshots[index].provider,
        ttlSeconds: spec.ttlMs / 1000,
        lastUpdated: snapshots[index].refreshedAt,
        errors: snapshots[index].errors,
      } satisfies CategoryMeta;
      return acc;
    },
    {} as Record<WatchlistKey, CategoryMeta>
  );

  return NextResponse.json({
    data: {
      ...data,
      refreshedAt,
    },
    meta: {
      categories: metaCategories,
    },
  });
}

async function getCategorySnapshot(key: WatchlistKey): Promise<CategorySnapshot> {
  const spec = CATEGORY_SPECS[key];
  const cacheEntry = categoryCache[key];
  if (cacheEntry && Date.now() - cacheEntry.timestamp < spec.ttlMs) {
    return cacheEntry.snapshot;
  }

  const persisted = snapshotStore.getSnapshotWithinTtl(key, spec.ttlMs);
  if (persisted && matchesWatchlist(persisted.items, spec.items)) {
    const snapshot: CategorySnapshot = {
      items: persisted.items,
      provider: persisted.provider,
      refreshedAt: persisted.refreshedAt,
      errors: [],
    };
    categoryCache[key] = { timestamp: Date.now(), snapshot };
    return snapshot;
  }
  if (persisted && !matchesWatchlist(persisted.items, spec.items)) {
    console.info(`Ignoring snapshot for ${key} because watchlist changed.`);
  }

  const attemptErrors: string[] = [];

  for (const provider of spec.providers) {
    try {
      const result = await fetchByProvider(provider, spec.items, key);
      if (!hasLiveQuotes(result.items, spec.requireComplete ?? false)) {
        attemptErrors.push(`${provider}:no-prices`);
        continue;
      }
      const snapshot: CategorySnapshot = {
        items: result.items,
        provider,
        refreshedAt: result.refreshedAt ?? new Date().toISOString(),
        errors: attemptErrors,
      };
      categoryCache[key] = { timestamp: Date.now(), snapshot };
      snapshotStore.saveSnapshot(key, snapshot);
      return snapshot;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      attemptErrors.push(`${provider}:${message}`);
      console.error(`Market ticker ${key} via ${provider} error:`, error);
    }
  }

  const staleSnapshot = snapshotStore.getLatestSnapshot(key);
  if (staleSnapshot) {
    const snapshot: CategorySnapshot = {
      items: staleSnapshot.items,
      provider: staleSnapshot.provider,
      refreshedAt: staleSnapshot.refreshedAt,
      errors: [...attemptErrors, 'snapshot-store:stale'],
    };
    categoryCache[key] = { timestamp: Date.now(), snapshot };
    return snapshot;
  }

  if (cacheEntry) {
    return {
      ...cacheEntry.snapshot,
      errors: [...cacheEntry.snapshot.errors, ...attemptErrors],
    };
  }

  return {
    items: spec.items.map((item) => ({ ...item, currency: item.currency ?? 'USD' })),
    provider: spec.providers[0],
    refreshedAt: null,
    errors: attemptErrors,
  };
}

async function fetchByProvider(provider: QuoteProvider, list: WatchItem[], category: WatchlistKey): Promise<ProviderResult> {
  switch (provider) {
    case 'stooq':
      return fetchStooqCategory(list);
    case 'coingecko':
      return fetchCoinGeckoCategory(list);
    case 'twelvedata':
      return fetchTwelveDataCategory(list, resolveTwelveDataKey(category));
    case 'alphavantage':
      return fetchAlphaVantageCategory(list, category);
    case 'marketstack':
      return fetchMarketstackCategory(list);
    case 'massive':
      return fetchMassiveCategory(list);
    default:
      throw new Error(`Unsupported provider: ${provider satisfies never}`);
  }
}

function resolveTwelveDataKey(category: WatchlistKey): string | null | undefined {
  if (category === 'commodities') {
    return twelvedataCommodityKey ?? twelvedataKey;
  }
  if (category === 'equities') {
    return twelvedataStocksKey ?? twelvedataKey;
  }
  return twelvedataKey;
}

interface StooqQuoteRow {
  symbol: string;
  open?: number;
  close?: number;
}

async function fetchStooqCategory(list: WatchItem[]): Promise<ProviderResult> {
  const symbols = list
    .map((item) => (item.providers?.stooq ?? item.symbol)?.toLowerCase())
    .filter((symbol): symbol is string => Boolean(symbol));

  if (!symbols.length) {
    return { items: list, refreshedAt: null };
  }

  const quotes = await downloadStooqQuotes(symbols);
  return {
    items: applyStooqQuotes(list, quotes),
    refreshedAt: new Date().toISOString(),
  };
}

type TwelveDataQuote = {
  symbol?: string;
  name?: string;
  price?: string;
  close?: string;
  percent_change?: string;
  currency?: string;
  datetime?: string;
  status?: string;
};

type CoinGeckoPriceRow = {
  usd?: number;
  usd_24h_change?: number;
  last_updated_at?: number;
};

const COINGECKO_SYMBOL_MAP: Record<string, string> = {
  BTCUSD: 'bitcoin',
  ETHUSD: 'ethereum',
  SOLUSD: 'solana',
  XRPUSD: 'ripple',
  DOGEUSD: 'dogecoin',
};

async function fetchTwelveDataCategory(list: WatchItem[], apiKey?: string | null): Promise<ProviderResult> {
  if (!apiKey) {
    throw new Error('TWELVEDATA_API_KEY is required for TwelveData quotes.');
  }

  const items = await fetchFromTwelveData(list, apiKey);
  const refreshedAt = new Date().toISOString();
  return { items, refreshedAt };
}

async function fetchCoinGeckoCategory(list: WatchItem[]): Promise<ProviderResult> {
  const targets = list
    .map((item) => ({
      item,
      id: (item.providers?.coingecko ?? COINGECKO_SYMBOL_MAP[item.symbol])?.toLowerCase(),
    }))
    .filter((entry): entry is { item: WatchItem; id: string } => Boolean(entry.id));

  if (!targets.length) {
    throw new Error('Missing CoinGecko identifiers for crypto watchlist.');
  }

  const ids = Array.from(new Set(targets.map((target) => target.id)));
  const params = {
    ids: ids.join(','),
    vs_currencies: 'usd',
    include_24hr_change: 'true',
    include_last_updated_at: 'true',
  } as const;

  const headers = coingeckoKey ? { 'x-cg-demo-api-key': coingeckoKey } : undefined;
  const response = await axios
    .get(`${COINGECKO_BASE_URL}/simple/price`, { params, headers })
    .catch((error) => {
      if (axios.isAxiosError(error)) {
        const detail = typeof error.response?.data?.error === 'string' ? error.response?.data?.error : error.message;
        throw new Error(`coingecko:${detail}`);
      }
      throw error;
    });
  const payload = response.data && typeof response.data === 'object' ? (response.data as Record<string, CoinGeckoPriceRow>) : {};

  let latest: string | null = null;
  const items = list.map((item) => {
    const id = (item.providers?.coingecko ?? COINGECKO_SYMBOL_MAP[item.symbol])?.toLowerCase();
    const quote = id ? payload[id] : undefined;
    const price = parseMaybeNumber(quote?.usd);
    const changePercent = parseMaybeNumber(quote?.usd_24h_change);
    const refreshed = typeof quote?.last_updated_at === 'number' ? toIsoFromTimestamp(quote.last_updated_at * 1000) : null;
    if (refreshed && (!latest || refreshed > latest)) {
      latest = refreshed;
    }

    return {
      ...item,
      currency: 'USD',
      price,
      changePercent,
    };
  });

  return {
    items,
    refreshedAt: latest,
  };
}

async function fetchAlphaVantageCategory(list: WatchItem[], category: WatchlistKey): Promise<ProviderResult> {
  if (category === 'forex') {
    return fetchAlphaVantageForex(list);
  }
  if (category === 'commodities') {
    return fetchAlphaVantageCommodities(list);
  }
  throw new Error(`Alpha Vantage provider not configured for "${category}".`);
}

async function fetchAlphaVantageForex(list: WatchItem[]): Promise<ProviderResult> {
  if (!alphaVantageForexKey) {
    throw new Error('ALPHA_VANTAGE_FOREX_API_KEY (or ALPHA_VANTAGE_API_KEY) is required for forex quotes.');
  }

  const items: MarketTickerItem[] = [];
  let latest: string | null = null;

  for (const item of list) {
    const pair = (item.providers?.alphavantage ?? item.symbol).toUpperCase();
    const { from, to } = splitForexSymbol(pair);
    const response = await requestAlphaVantage(
      {
        function: 'CURRENCY_EXCHANGE_RATE',
        from_currency: from,
        to_currency: to,
      },
      alphaVantageForexKey
    );

    const block: Record<string, string> | undefined = response.data?.['Realtime Currency Exchange Rate'];
    if (!block) {
      const note = response.data?.Note ?? response.data?.['Error Message'];
      throw new Error(note ?? 'Alpha Vantage returned an empty payload.');
    }

    const exchangeRate = parseMaybeNumber(block['5. Exchange Rate']);
    const refreshed = toIsoTimestamp(block['6. Last Refreshed']);
    if (refreshed && (!latest || refreshed > latest)) {
      latest = refreshed;
    }

    items.push({
      ...item,
      currency: to,
      price: exchangeRate,
      changePercent: undefined,
    });
  }

  return {
    items,
    refreshedAt: latest,
  };
}

type AlphaCommodityQuote = {
  price?: number;
  changePercent?: number;
  refreshedAt: string | null;
};

// Rate limiting: Alpha Vantage free tier allows 1 request per second
const ALPHA_VANTAGE_RATE_LIMIT_MS = 1200; // 1.2 seconds to be safe
let lastAlphaVantageRequest = 0;

async function alphaVantageRateLimitDelay(): Promise<void> {
  const now = Date.now();
  const elapsed = now - lastAlphaVantageRequest;
  if (elapsed < ALPHA_VANTAGE_RATE_LIMIT_MS) {
    await new Promise((resolve) => setTimeout(resolve, ALPHA_VANTAGE_RATE_LIMIT_MS - elapsed));
  }
  lastAlphaVantageRequest = Date.now();
}

async function fetchAlphaVantageCommodities(list: WatchItem[]): Promise<ProviderResult> {
  if (!alphaVantageCommodityKey) {
    throw new Error('ALPHA_VANTAGE_API_KEY (or ALPHA_VANTAGE_FOREX_API_KEY) is required for commodity quotes.');
  }

  const timestampCandidates: Array<string | null> = [];
  const items: MarketTickerItem[] = [];

  for (const item of list) {
    const spec = ALPHA_COMMODITY_SPECS[item.symbol];
    if (!spec) {
      // Skip items without mapping instead of throwing
      console.warn(`Missing Alpha Vantage commodity mapping for ${item.symbol}, skipping`);
      items.push({ ...item, currency: item.currency ?? 'USD' });
      continue;
    }

    try {
      // Apply rate limiting before each request
      await alphaVantageRateLimitDelay();
      
      const quote: AlphaCommodityQuote =
        spec.mode === 'dailySeries'
          ? await loadAlphaDailySeriesQuote(spec.symbol, alphaVantageCommodityKey)
          : await loadAlphaMacroCommodityQuote(spec.function, spec.interval, alphaVantageCommodityKey);

      timestampCandidates.push(quote.refreshedAt);
      items.push({
        ...item,
        currency: item.currency ?? 'USD',
        price: quote.price,
        changePercent: quote.changePercent,
      });
    } catch (error) {
      // If rate limited, add item without price and continue
      const message = error instanceof Error ? error.message : String(error);
      if (message.includes('rate limit') || message.includes('Thank you for using Alpha Vantage')) {
        console.warn(`Alpha Vantage rate limited for ${item.symbol}, skipping remaining items`);
        // Add remaining items without prices
        items.push({ ...item, currency: item.currency ?? 'USD' });
        // Don't continue fetching - rate limit affects all requests
        break;
      }
      throw error;
    }
  }

  return {
    items,
    refreshedAt: getLatestTimestamp(timestampCandidates),
  };
}

async function loadAlphaDailySeriesQuote(symbol: string, apiKey: string): Promise<AlphaCommodityQuote> {
  const response = await requestAlphaVantage(
    {
      function: 'TIME_SERIES_DAILY',
      symbol,
      outputsize: 'compact',
    },
    apiKey
  );

  const series = response.data?.['Time Series (Daily)'];
  if (!series || typeof series !== 'object') {
    const note = response.data?.Note ?? response.data?.['Error Message'];
    throw new Error(note ?? `Alpha Vantage returned no daily series for ${symbol}`);
  }

  const entries = Object.entries(series as Record<string, Record<string, string>>)
    .filter(([date]) => Boolean(date))
    .sort(([a], [b]) => (a > b ? -1 : 1));

  if (!entries.length) {
    throw new Error(`Alpha Vantage returned an empty daily series for ${symbol}`);
  }

  const [latestDate, latestRow] = entries[0];
  const price =
    parseMaybeNumber(latestRow['4. close']) ??
    parseMaybeNumber(latestRow['5. adjusted close']) ??
    parseMaybeNumber(latestRow['4. Close']);

  const previousRow = entries[1]?.[1];
  const previousClose = previousRow
    ? parseMaybeNumber(previousRow['4. close']) ?? parseMaybeNumber(previousRow['5. adjusted close'])
    : undefined;

  const changePercent =
    typeof price === 'number' && typeof previousClose === 'number'
      ? computeChangePercent(price - previousClose, previousClose)
      : undefined;

  return {
    price,
    changePercent,
    refreshedAt: toIsoTimestamp(latestDate),
  };
}

async function loadAlphaMacroCommodityQuote(
  func: AlphaMacroCommodityFunction,
  interval: 'daily' | 'weekly' | 'monthly',
  apiKey: string
): Promise<AlphaCommodityQuote> {
  const response = await requestAlphaVantage(
    {
      function: func,
      interval,
    },
    apiKey
  );

  const rows = (Array.isArray(response.data?.data) ? response.data.data : []) as Record<string, unknown>[];
  const parsed = rows
    .map((row) => ({
      date: typeof row?.date === 'string' ? row.date : null,
      value: parseMaybeNumber(row?.value),
    }))
    .filter((entry): entry is { date: string; value: number } => Boolean(entry.date) && typeof entry.value === 'number')
    .sort((a, b) => (a.date > b.date ? -1 : 1));

  if (!parsed.length) {
    const note = response.data?.Note ?? response.data?.['Error Message'];
    throw new Error(note ?? `Alpha Vantage returned no data for ${func}`);
  }

  const latest = parsed[0];
  const previous = parsed[1];
  const changePercent =
    previous?.value !== undefined
      ? computeChangePercent(latest.value - previous.value, previous.value)
      : undefined;

  return {
    price: latest.value,
    changePercent,
    refreshedAt: toIsoTimestamp(latest.date),
  };
}

type MarketstackQuote = {
  symbol?: string;
  date?: string;
  open?: number;
  close?: number;
  last?: number;
};

type MassiveSummaryResult = {
  ticker?: string;
  price?: number | string;
  session?: {
    change?: number | string;
    change_percent?: number | string;
    previous_close?: number | string;
    close?: number | string;
    price?: number | string;
  };
  last_updated?: number | string;
};

type MassiveFuturesSnapshot = {
  product_code?: string;
  ticker?: string;
  last_trade?: {
    price?: number | string;
    last_updated?: number | string;
  };
  last_quote?: {
    ask?: number | string;
    bid?: number | string;
    last_updated?: number | string;
  };
  last_minute?: {
    last_updated?: number | string;
  };
  session?: {
    change?: number | string;
    change_percent?: number | string;
    previous_settlement?: number | string;
    settlement_price?: number | string;
    close?: number | string;
  };
  details?: {
    settlement_date?: number | string;
  };
};

async function fetchMarketstackCategory(list: WatchItem[]): Promise<ProviderResult> {
  if (!marketstackKey) {
    throw new Error('MARKETSTACK_API_KEY is required for commodity quotes.');
  }

  const symbols = Array.from(
    new Set(
      list
        .map((item) => (item.providers?.marketstack ?? item.symbol)?.toUpperCase())
        .filter((symbol): symbol is string => Boolean(symbol))
    )
  );

  if (!symbols.length) {
    return { items: list, refreshedAt: null };
  }

  const response = await axios.get(`${MARKETSTACK_BASE_URL}/eod/latest`, {
    params: {
      access_key: marketstackKey,
      symbols: symbols.join(','),
      limit: symbols.length,
    },
  });

  if (response.data?.error) {
    const message = response.data.error?.message ?? 'MarketStack returned an error response.';
    throw new Error(message);
  }

  const rows: MarketstackQuote[] = Array.isArray(response.data?.data) ? response.data.data : [];
  const lookup = new Map<string, MarketstackQuote>();
  for (const row of rows) {
    const symbol = typeof row?.symbol === 'string' ? row.symbol.toUpperCase() : undefined;
    if (symbol) {
      lookup.set(symbol, row);
    }
  }

  let latest: string | null = null;
  const items: MarketTickerItem[] = list.map((item) => {
    const providerSymbol = (item.providers?.marketstack ?? item.symbol).toUpperCase();
    const quote = lookup.get(providerSymbol);
    if (quote?.date) {
      const iso = toIsoTimestamp(quote.date);
      if (iso && (!latest || iso > latest)) {
        latest = iso;
      }
    }
    const price = quote ? parseMaybeNumber(quote.close ?? quote.last) : undefined;
    const changePercent =
      quote?.open && quote?.open !== 0 && price !== undefined
        ? ((price - quote.open) / quote.open) * 100
        : undefined;

    return {
      ...item,
      currency: item.currency ?? 'USD',
      price,
      changePercent,
    };
  });

  return {
    items,
    refreshedAt: latest,
  };
}

async function fetchMassiveCategory(list: WatchItem[]): Promise<ProviderResult> {
  if (!massiveKey) {
    throw new Error('MASSIVE_API_KEY is required for Massive quotes.');
  }

  const massiveAuthHeaders = {
    Authorization: `Bearer ${massiveKey}`,
  } as const;

  type SummaryTarget = { ticker: string; item: WatchItem };
  type FuturesTarget = { productCode: string; item: WatchItem };

  const summaryTargets: SummaryTarget[] = [];
  const futuresTargets: FuturesTarget[] = [];

  for (const item of list) {
    const raw = (item.providers?.massive ?? item.symbol)?.trim();
    if (!raw) {
      continue;
    }
    if (raw.toLowerCase().startsWith('product:')) {
      const productCode = raw.slice('product:'.length).toUpperCase();
      if (productCode) {
        futuresTargets.push({ productCode, item });
      }
      continue;
    }
    summaryTargets.push({ ticker: raw, item });
  }

  const assignments = new Map<string, MarketTickerItem>();
  const timestampCandidates: Array<string | null> = [];

  if (summaryTargets.length) {
    const tickers = Array.from(new Set(summaryTargets.map((entry) => entry.ticker)));
    const response = await axios.get(`${MASSIVE_BASE_URL}/v1/summaries`, {
      headers: massiveAuthHeaders,
      params: {
        apiKey: massiveKey,
        'ticker.any_of': tickers.join(','),
      },
    });

    const rawResults = Array.isArray(response.data?.results) ? (response.data.results as MassiveSummaryResult[]) : [];
    const lookup = new Map<string, MassiveSummaryResult>();
    for (const row of rawResults) {
      if (typeof row?.ticker === 'string') {
        lookup.set(row.ticker, row);
      }
    }

    for (const target of summaryTargets) {
      const snapshot = lookup.get(target.ticker);
      if (!snapshot) {
        continue;
      }
      const session = snapshot.session;
      const price = parseMaybeNumber(snapshot.price ?? session?.price ?? session?.close);
      const changePercent = computeChangePercent(
        parseMaybeNumber(session?.change),
        parseMaybeNumber(session?.previous_close),
        parseMaybeNumber(session?.change_percent)
      );
      const refreshed = toIsoFromTimestamp(parseMaybeNumber(snapshot.last_updated));
      timestampCandidates.push(refreshed);
      assignments.set(target.item.symbol, {
        ...target.item,
        currency: target.item.currency ?? 'USD',
        price,
        changePercent,
      });
    }
  }

  if (futuresTargets.length) {
    const productCodes = Array.from(new Set(futuresTargets.map((entry) => entry.productCode)));
    const snapshotLimit = Math.min(Math.max(productCodes.length * 25, 25), 500);
    const response = await axios.get(`${MASSIVE_BASE_URL}/futures/vX/snapshot`, {
      headers: massiveAuthHeaders,
      params: {
        apiKey: massiveKey,
        'product_code.any_of': productCodes.join(','),
        limit: snapshotLimit,
      },
    });

    const rawResults = Array.isArray(response.data?.results) ? (response.data.results as MassiveFuturesSnapshot[]) : [];
    const grouped = new Map<string, MassiveFuturesSnapshot>();
    for (const row of rawResults) {
      const productCode = typeof row?.product_code === 'string' ? row.product_code.toUpperCase() : undefined;
      if (!productCode) {
        continue;
      }
      const current = grouped.get(productCode);
      if (!current) {
        grouped.set(productCode, row);
        continue;
      }
      const currentDate = parseMaybeNumber(current.details?.settlement_date) ?? Number.MAX_VALUE;
      const candidateDate = parseMaybeNumber(row.details?.settlement_date) ?? Number.MAX_VALUE;
      if (candidateDate < currentDate) {
        grouped.set(productCode, row);
      }
    }

    for (const target of futuresTargets) {
      const snapshot = grouped.get(target.productCode);
      if (!snapshot) {
        continue;
      }
      const session = snapshot.session;
      const price =
        parseMaybeNumber(snapshot.last_trade?.price) ??
        parseMaybeNumber(session?.settlement_price) ??
        parseMaybeNumber(session?.close) ??
        parseMaybeNumber(snapshot.last_quote?.bid);
      const changePercent = computeChangePercent(
        parseMaybeNumber(session?.change),
        parseMaybeNumber(session?.previous_settlement),
        parseMaybeNumber(session?.change_percent)
      );
      const refreshed = toIsoFromTimestamp(
        parseMaybeNumber(snapshot.last_trade?.last_updated) ??
          parseMaybeNumber(snapshot.last_quote?.last_updated) ??
          parseMaybeNumber(snapshot.last_minute?.last_updated)
      );
      timestampCandidates.push(refreshed);
      assignments.set(target.item.symbol, {
        ...target.item,
        currency: target.item.currency ?? 'USD',
        price,
        changePercent,
      });
    }
  }

  const refreshedAt = getLatestTimestamp(timestampCandidates);
  const items = list.map((item) => assignments.get(item.symbol) ?? { ...item, currency: item.currency ?? 'USD' });

  return {
    items,
    refreshedAt,
  };
}

async function downloadStooqQuotes(symbols: string[]): Promise<Record<string, StooqQuoteRow>> {
  if (!symbols.length) {
    return {};
  }

  const uniqueSymbols = Array.from(new Set(symbols));
  const params = new URLSearchParams({
    s: uniqueSymbols.join('+'),
    f: 'sd2t2ohlcv',
    e: 'csv',
    h: '1',
  });

  const response = await axios.get(`${STOOQ_QUOTE_URL}?${params.toString()}`, {
    responseType: 'text',
  });

  return parseStooqCsv(response.data);
}

function parseStooqCsv(text: string): Record<string, StooqQuoteRow> {
  const trimmed = text.trim();
  if (!trimmed) {
    return {};
  }

  const [headerLine, ...rows] = trimmed.split(/\r?\n/).filter(Boolean);
  const headers = headerLine.split(',');
  const idx = (key: string) => headers.findIndex((column) => column.toLowerCase() === key.toLowerCase());
  const symbolIdx = idx('Symbol');
  const openIdx = idx('Open');
  const closeIdx = idx('Close');

  const result: Record<string, StooqQuoteRow> = {};

  for (const row of rows) {
    const cells = row.split(',');
    const symbol = cells[symbolIdx]?.trim();
    if (!symbol || symbol === 'N/D') {
      continue;
    }
    const open = cells[openIdx]?.trim();
    const close = cells[closeIdx]?.trim();
    const normalizedSymbol = symbol.toLowerCase();
    result[normalizedSymbol] = {
      symbol,
      open: parseMaybeNumber(open),
      close: parseMaybeNumber(close),
    };
  }

  return result;
}

function applyStooqQuotes(list: WatchItem[], quotes?: Record<string, StooqQuoteRow>): MarketTickerItem[] {
  return list.map((item) => {
    const providerSymbol = (item.providers?.stooq ?? item.symbol)?.toLowerCase();
    const quote = providerSymbol && quotes ? quotes[providerSymbol] : undefined;
    const price = quote?.close;
    const changePercent =
      quote?.open && quote?.open !== 0 && price !== undefined
        ? ((price - quote.open) / quote.open) * 100
        : undefined;

    return {
      ...item,
      currency: item.currency ?? 'USD',
      price,
      changePercent,
    };
  });
}

function normalizeTwelveDataResponse(raw: unknown): Record<string, TwelveDataQuote> {
  if (!raw || typeof raw !== 'object') {
    return {};
  }

  if ('status' in raw && (raw as Record<string, unknown>).status === 'error') {
    return {};
  }

  if ('symbol' in raw) {
    const quote = raw as TwelveDataQuote;
    const key = quote.symbol ?? '';
    return key ? { [key]: quote } : {};
  }

  return raw as Record<string, TwelveDataQuote>;
}

async function fetchFromTwelveData(list: WatchItem[], apiKey: string): Promise<MarketTickerItem[]> {
  const mapped = list
    .map((item) => ({ item, symbol: item.providers?.twelvedata ?? item.symbol }))
    .filter(({ symbol }) => Boolean(symbol));

  if (!mapped.length) {
    return list;
  }

  const uniqueSymbols = Array.from(new Set(mapped.map(({ symbol }) => symbol)));

  const response = await axios.get(`${TWELVEDATA_BASE_URL}/quote`, {
    params: {
      symbol: uniqueSymbols.join(','),
      apikey: apiKey,
    },
  });

  const normalized = normalizeTwelveDataResponse(response.data);

  return list.map((item) => {
    const providerSymbol = item.providers?.twelvedata ?? item.symbol;
    const quote = providerSymbol ? normalized[providerSymbol] : undefined;
    const price = quote ? parseMaybeNumber(quote.price ?? quote.close) : undefined;
    const changePercent = quote ? parseMaybeNumber(quote.percent_change) : undefined;

    return {
      ...item,
      currency: quote?.currency ?? item.currency ?? 'USD',
      price,
      changePercent,
    };
  });
}

type AlphaVantageParams = Record<string, string | number | boolean | undefined>;

async function requestAlphaVantage(params: AlphaVantageParams, preferredKey?: string | null) {
  const candidateKeys = [preferredKey, alphaVantageRetryKey]
    .filter((key): key is string => Boolean(key))
    .filter((key, index, arr) => arr.indexOf(key) === index);

  if (!candidateKeys.length) {
    throw new Error('Alpha Vantage API key is required.');
  }

  let lastError: Error | null = null;

  for (let index = 0; index < candidateKeys.length; index++) {
    const key = candidateKeys[index];
    const isLastAttempt = index === candidateKeys.length - 1;
    try {
      const response = await axios.get(ALPHA_VANTAGE_BASE_URL, {
        params: {
          ...params,
          apikey: key,
        },
      });
      const limitMessage = getAlphaLimitMessage(response.data);
      if (limitMessage) {
        lastError = new Error(limitMessage);
        if (isLastAttempt) {
          throw lastError;
        }
        continue;
      }
      return response;
    } catch (error) {
      if (shouldRetryAlphaError(error) && !isLastAttempt) {
        lastError = error instanceof Error ? error : new Error(String(error));
        continue;
      }
      throw error;
    }
  }

  if (lastError) {
    throw lastError;
  }
  throw new Error('Alpha Vantage request failed.');
}

function getAlphaLimitMessage(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const note = typeof (payload as Record<string, unknown>).Note === 'string' ? (payload as Record<string, string>).Note : null;
  const info = typeof (payload as Record<string, unknown>).Information === 'string' ? (payload as Record<string, string>).Information : null;
  const message = note ?? info;
  if (!message) {
    return null;
  }
  const normalized = message.toLowerCase();
  if (normalized.includes('thank you for using alpha vantage') || normalized.includes('premium support') || normalized.includes('frequency')) {
    return message;
  }
  return null;
}

function shouldRetryAlphaError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) {
    return false;
  }
  const status = error.response?.status;
  if (status === 429) {
    return true;
  }
  return Boolean(getAlphaLimitMessage(error.response?.data));
}

function parseMaybeNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

function splitForexSymbol(symbol: string): { from: string; to: string } {
  if (symbol.length === 6) {
    return { from: symbol.slice(0, 3), to: symbol.slice(3, 6) };
  }
  const match = symbol.match(/([A-Z]{3})[\/_-]?([A-Z]{3})/);
  if (match) {
    return { from: match[1], to: match[2] };
  }
  throw new Error(`Unable to parse forex symbol "${symbol}"`);
}

function toIsoFromTimestamp(value?: number): string | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return null;
  }
  const milliseconds = value > 1e15 ? value / 1_000_000 : value;
  const date = new Date(milliseconds);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function toIsoTimestamp(value?: string): string | null {
  if (!value) {
    return null;
  }
  const normalized = /[zZ+]/.test(value) ? value : `${value}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function getLatestTimestamp(values: Array<string | null>): string | null {
  const timestamps = values
    .map((value) => (value ? Date.parse(value) : NaN))
    .filter((time) => Number.isFinite(time)) as number[];

  if (!timestamps.length) {
    return null;
  }

  return new Date(Math.max(...timestamps)).toISOString();
}

function hasLiveQuotes(items: MarketTickerItem[], requireComplete = false): boolean {
  const hasPrice = (item: MarketTickerItem) => typeof item.price === 'number' && Number.isFinite(item.price);
  return requireComplete ? items.every(hasPrice) : items.some(hasPrice);
}

function computeChangePercent(change?: number, baseline?: number, fallback?: number): number | undefined {
  if (typeof change === 'number' && typeof baseline === 'number' && baseline !== 0) {
    return (change / baseline) * 100;
  }
  if (typeof fallback === 'number') {
    return fallback;
  }
  return undefined;
}

function matchesWatchlist(snapshotItems: MarketTickerItem[], specItems: WatchItem[]): boolean {
  if (snapshotItems.length !== specItems.length) {
    return false;
  }
  const expected = new Set(specItems.map((item) => item.symbol));
  for (const item of snapshotItems) {
    if (!expected.has(item.symbol)) {
      return false;
    }
  }
  return true;
}
