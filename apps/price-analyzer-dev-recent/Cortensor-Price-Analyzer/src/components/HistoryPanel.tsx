"use client";

import { useEffect, useMemo, useState } from 'react';
import type { ChangeEvent, KeyboardEvent, MouseEvent } from 'react';
import { HistoryService, HistoryItem } from '@/lib/historyService';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Clock3,
  History as HistoryIcon,
  LineChart,
  Search,
  Sparkles,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface HistoryPanelProps {
  onLoadHistoryItem: (item: HistoryItem) => void;
  onHistoryChange?: () => void;
  className?: string;
}

interface HistoryStats {
  total: number;
  oldestDate: Date | null;
}

export function HistoryPanel({ onLoadHistoryItem, onHistoryChange, className }: HistoryPanelProps) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [query, setQuery] = useState('');
  const [stats, setStats] = useState<HistoryStats>({ total: 0, oldestDate: null });

  useEffect(() => {
    refreshHistory();
  }, []);

  useEffect(() => {
    setStats(HistoryService.getHistoryStats());
  }, [history]);

  const filteredHistory = useMemo(() => {
    if (!query.trim()) return history;
    return HistoryService.searchHistory(query.trim());
  }, [query, history]);

  const refreshHistory = () => {
    const items = HistoryService.getHistory();
    setHistory(items);
  };

  const handleLoad = (item: HistoryItem) => {
    onLoadHistoryItem(item);
  };

  const handleDelete = (event: MouseEvent<HTMLButtonElement>, id: string) => {
    event.stopPropagation();
    HistoryService.deleteHistoryItem(id);
    refreshHistory();
    onHistoryChange?.();
  };

  const handleKeyLoad = (event: KeyboardEvent<HTMLDivElement>, item: HistoryItem) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleLoad(item);
    }
  };

  const handleClear = () => {
    if (typeof window !== 'undefined' && window.confirm('Clear all saved analyses?')) {
      HistoryService.clearHistory();
      refreshHistory();
      onHistoryChange?.();
    }
  };

  const handleSearchChange = (event: ChangeEvent<HTMLInputElement>) => {
    setQuery(event.target.value);
  };

  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const renderEmpty = () => (
    <div className="flex flex-col items-center justify-center gap-3 py-10 text-center text-sm text-muted-foreground">
      <HistoryIcon className="h-10 w-10 text-blue-500" />
      <p className="font-medium text-slate-700">No saved analyses yet</p>
      <p className="max-w-xs text-xs text-muted-foreground">
        Run a market scan and it will be saved here for quick access and comparisons.
      </p>
    </div>
  );

  return (
    <Card className={cn('border-2 border-blue-100 bg-slate-50/60 backdrop-blur-sm', className)}>
      <CardHeader className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <HistoryIcon className="h-5 w-5 text-blue-600" />
              Saved Analyses
            </CardTitle>
            <CardDescription>
              {stats.total > 0
                ? `${stats.total} stored ${stats.total === 1 ? 'analysis' : 'analyses'}`
                : 'Snapshots from your recent market scans'}
            </CardDescription>
          </div>
          {history.length > 0 && (
            <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-600" onClick={handleClear}>
              <Trash2 className="mr-2 h-4 w-4" />
              Clear
            </Button>
          )}
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Search ticker, company, or narrative keywords"
            value={query}
            onChange={handleSearchChange}
            className="pl-9"
            aria-label="Search saved analyses"
          />
        </div>
        {stats.oldestDate && (
          <p className="text-xs text-muted-foreground">
            Tracking history since {stats.oldestDate.toLocaleDateString()}
          </p>
        )}
      </CardHeader>
      <Separator />
      <CardContent className="space-y-4">
        {filteredHistory.length === 0 ? (
          renderEmpty()
        ) : (
          <div className="space-y-3">
            {filteredHistory.map((item) => (
              <div
                key={item.id}
                role="button"
                tabIndex={0}
                onClick={() => handleLoad(item)}
                onKeyDown={(event) => handleKeyLoad(event, item)}
                className="group w-full rounded-xl border border-slate-200 bg-white/70 p-4 text-left shadow-sm transition hover:border-blue-300 hover:bg-blue-50/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="uppercase text-xs tracking-wide">
                      {item.ticker}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {item.assetType.toUpperCase()}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {item.horizon}
                    </Badge>
                    {item.changePercent !== undefined && (
                      <span
                        className={cn(
                          'text-xs font-semibold',
                          (item.changePercent ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-500',
                        )}
                      >
                        {(item.changePercent ?? 0) >= 0 ? '+' : ''}{item.changePercent?.toFixed(2)}%
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Clock3 className="h-4 w-4" />
                    {formatTimestamp(item.timestamp)}
                  </div>
                </div>
                <div className="mt-3 space-y-2 text-sm text-slate-700">
                  <p className="font-semibold text-slate-900">
                    {item.companyName ? `${item.companyName} (${item.ticker})` : item.ticker}
                  </p>
                  <p className="line-clamp-3 text-xs text-muted-foreground">{item.previewText}</p>
                </div>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-1 font-medium text-blue-600">
                      <Sparkles className="h-3.5 w-3.5" />
                      AI Summary
                    </span>
                    <span className="inline-flex items-center gap-1 text-slate-500">
                      <LineChart className="h-3.5 w-3.5" />
                      {item.report.technicals.rsi14 ? `RSI ${item.report.technicals.rsi14.toFixed(1)}` : 'RSI —'}
                    </span>
                    {item.report.fundamentals.peRatio && (
                      <span className="text-slate-500">P/E {item.report.fundamentals.peRatio.toFixed(1)}</span>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(event) => handleDelete(event, item.id)}
                    className="h-8 w-8 text-slate-400 hover:text-red-500"
                    aria-label="Delete saved analysis"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}