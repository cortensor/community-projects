'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, RefreshCw, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type AssetKind = 'equity' | 'crypto' | 'forex' | 'commodity';

type MarketTickerItem = {
  symbol: string;
  name: string;
  type: AssetKind;
  price?: number;
  changePercent?: number;
  currency?: string;
};

type MarketTickerGroups = {
  equities: MarketTickerItem[];
  crypto: MarketTickerItem[];
  forex: MarketTickerItem[];
  commodities: MarketTickerItem[];
};

type MarketTickerResponse = MarketTickerGroups & { refreshedAt?: string };

const CATEGORY_CONFIG: Record<keyof MarketTickerGroups, { title: string; badge: string; description: string }> = {
  equities: { title: 'US Equities Focus', badge: 'Stocks', description: 'Growth + mega-cap movers' },
  crypto: { title: 'Crypto Majors', badge: 'Digital Assets', description: 'Layer-1 and top memecoins' },
  forex: { title: 'FX Pairs', badge: 'Forex', description: 'G10 volatility snapshot' },
  commodities: { title: 'Macro Commodities', badge: 'Commodities', description: 'Energy & precious metals' },
};

const CURRENCY_SYMBOL: Record<string, string> = {
  USD: '$',
  EUR: '€',
  GBP: '£',
  JPY: '¥',
};

export function MarketTickerSidebar() {
  const [data, setData] = useState<MarketTickerResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<keyof MarketTickerGroups>('equities');
  const [userCategoryOverride, setUserCategoryOverride] = useState(false);
  const swipeRef = useRef<HTMLDivElement | null>(null);

  const loadTickers = useCallback(async () => {
    try {
      setRefreshing(true);
      const response = await fetch('/api/market-tickers');
      if (!response.ok) {
        throw new Error('Failed to load live quotes.');
      }
      const payload = await response.json();
      setData(payload.data ?? null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to retrieve quote data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const categories = useMemo(() => Object.keys(CATEGORY_CONFIG) as Array<keyof MarketTickerGroups>, []);

  const categoryHasPrices = useCallback(
    (category: keyof MarketTickerGroups) =>
      Boolean(data?.[category]?.some((item) => typeof item.price === 'number')),
    [data]
  );

  const handleNextCategory = useCallback(() => {
    setUserCategoryOverride(true);
    setActiveCategory((current) => {
      const index = categories.indexOf(current);
      const nextIndex = index === categories.length - 1 ? 0 : index + 1;
      return categories[nextIndex];
    });
  }, [categories]);

  const handlePrevCategory = useCallback(() => {
    setUserCategoryOverride(true);
    setActiveCategory((current) => {
      const index = categories.indexOf(current);
      const prevIndex = index === 0 ? categories.length - 1 : index - 1;
      return categories[prevIndex];
    });
  }, [categories]);

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'ArrowLeft') {
        handlePrevCategory();
      } else if (event.key === 'ArrowRight') {
        handleNextCategory();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [categories, handleNextCategory, handlePrevCategory]);

  useEffect(() => {
    const node = swipeRef.current;
    if (!node) return;

    let startX = 0;

    const onTouchStart = (event: TouchEvent) => {
      startX = event.touches[0]?.clientX ?? 0;
    };

    const onTouchEnd = (event: TouchEvent) => {
      const endX = event.changedTouches[0]?.clientX ?? 0;
      const delta = endX - startX;
      if (Math.abs(delta) < 40) return;
      if (delta > 0) {
        handlePrevCategory();
      } else {
        handleNextCategory();
      }
    };

    node.addEventListener('touchstart', onTouchStart);
    node.addEventListener('touchend', onTouchEnd);
    return () => {
      node.removeEventListener('touchstart', onTouchStart);
      node.removeEventListener('touchend', onTouchEnd);
    };
  }, [handleNextCategory, handlePrevCategory]);

  useEffect(() => {
    loadTickers();
  }, [loadTickers]);

  useEffect(() => {
    if (!data || userCategoryOverride) {
      return;
    }
    if (categoryHasPrices(activeCategory)) {
      return;
    }

    const fallback = categories.find((category) => categoryHasPrices(category));
    if (fallback && fallback !== activeCategory) {
      setActiveCategory(fallback);
    }
  }, [data, activeCategory, categories, categoryHasPrices, userCategoryOverride]);

  const updatedLabel = data?.refreshedAt
    ? new Date(data.refreshedAt).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
    : null;
  const activeCategoryHasPrices = categoryHasPrices(activeCategory);

  const renderItems = (items: MarketTickerItem[]) => {
    if (!items.length) {
      return <p className="text-xs text-muted-foreground">No symbols available yet.</p>;
    }

    return (
      <div className="space-y-2">
        {items.map((item) => (
          <div
            key={item.symbol}
            className="flex items-center justify-between rounded-xl border border-slate-200 bg-white/90 px-3 py-2"
          >
            <div>
              <p className="text-sm font-semibold text-slate-900">{item.symbol}</p>
              <p className="text-xs text-muted-foreground">{item.name}</p>
            </div>
            <div className="text-right">
              <p className="text-sm font-semibold text-slate-900">
                {formatPrice(item.price, item.currency)}
                {item.currency && (
                  <span className="ml-1 text-[11px] text-muted-foreground">{item.currency}</span>
                )}
              </p>
              <p className={cn('text-xs font-semibold', getChangeColor(item.changePercent))}>
                {formatChange(item.changePercent)}
              </p>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <Card className="border-2 border-blue-100 bg-gradient-to-b from-white to-blue-50/40 shadow-sm">
      <CardHeader className="space-y-1">
        <div className="flex items-center gap-2 text-blue-700">
          <TrendingUp className="h-5 w-5" />
          <CardTitle className="text-base">Market Pulse</CardTitle>
        </div>
        <CardDescription>
          Curated watchlists spanning equities, crypto, FX, and macro commodities powered by Stooq + Twelve Data.
        </CardDescription>
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-muted-foreground">
            {updatedLabel ? `Last sync ${updatedLabel}` : 'Waiting for live data...'}
          </span>
          <Button variant="ghost" size="sm" onClick={loadTickers} disabled={refreshing} className="text-xs">
            <RefreshCw className={cn('mr-2 h-4 w-4', refreshing && 'animate-spin')} />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && !loading && (
          <Alert variant="destructive">
            <AlertDescription className="text-xs">{error}</AlertDescription>
          </Alert>
        )}
        {loading && (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-16 animate-pulse rounded-xl bg-slate-100" />
            ))}
          </div>
        )}
        {!loading && data && (
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-2xl border border-blue-100 bg-white/80 p-3">
              <div>
                <p className="text-sm font-semibold text-slate-800 flex items-center gap-2">
                  {CATEGORY_CONFIG[activeCategory].title}
                  <Badge variant="secondary" className="text-[11px]">
                    {CATEGORY_CONFIG[activeCategory].badge}
                  </Badge>
                </p>
                <p className="text-xs text-muted-foreground">
                  {CATEGORY_CONFIG[activeCategory].description}
                </p>
                {!activeCategoryHasPrices && (
                  <p className="text-[11px] text-amber-600">Live pricing unavailable — refresh or switch views.</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label="Previous category"
                  onClick={handlePrevCategory}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label="Next category"
                  onClick={handleNextCategory}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <section
              ref={swipeRef}
              className="rounded-2xl border border-slate-200 bg-white/80 p-3"
              aria-live="polite"
            >
              {renderItems(data[activeCategory] ?? [])}
            </section>
            <div className="flex items-center justify-center gap-2">
              {categories.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={cn(
                    'h-2.5 w-2.5 rounded-full transition',
                    activeCategory === key ? 'bg-blue-600' : 'bg-slate-300 hover:bg-slate-400'
                  )}
                  aria-label={`Show ${CATEGORY_CONFIG[key].title}`}
                  onClick={() => {
                    setUserCategoryOverride(true);
                    setActiveCategory(key);
                  }}
                />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function formatPrice(value?: number, currency = 'USD'): string {
  if (value === undefined || Number.isNaN(value)) {
    return '—';
  }
  const symbol = CURRENCY_SYMBOL[currency] ?? '';
  const abs = Math.abs(value);
  const digits = abs >= 100 ? 2 : abs >= 1 ? 3 : 4;
  return `${symbol}${value.toFixed(digits)}`;
}

function formatChange(value?: number): string {
  if (value === undefined || Number.isNaN(value)) {
    return '—';
  }
  const display = value.toFixed(2);
  return `${value >= 0 ? '+' : ''}${display}%`;
}

function getChangeColor(value?: number): string {
  if (value === undefined || Number.isNaN(value)) {
    return 'text-slate-500';
  }
  return value >= 0 ? 'text-emerald-600' : 'text-red-600';
}
