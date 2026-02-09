import { NextRequest, NextResponse } from 'next/server';
import { MarketDataService, MarketDataError } from '@/lib/marketDataService';
import { NewsService } from '@/lib/newsService';
import { CortensorService } from '@/lib/cortensorService';
import { marketCache } from '@/lib/cacheService';
import type { CacheTTL } from '@/lib/cacheService';
import type { AnalysisHorizon, AnalyzerResponse, AssetType, MarketAnalysisContext } from '@/lib/marketTypes';

function ttlTypeForAsset(assetType: AssetType): keyof CacheTTL {
  switch (assetType) {
    case 'equity':
      return 'equity';
    case 'etf':
      return 'etf';
    case 'crypto':
      return 'crypto';
    case 'forex':
      return 'forex';
    case 'commodity':
      return 'commodity';
    default:
      return 'default';
  }
}

interface AnalyzerRequestBody {
  ticker?: string;
  assetType?: AssetType;
  horizon?: AnalysisHorizon;
  skipCache?: boolean;
}

const DEFAULT_ASSET_TYPE: AssetType = 'equity';
const DEFAULT_HORIZON: AnalysisHorizon = '3M';

export async function POST(request: NextRequest) {
  const startTime = Date.now();
  
  try {
    const body = (await request.json()) as AnalyzerRequestBody;
    const ticker = body.ticker?.trim().toUpperCase();
    const assetType: AssetType = body.assetType || DEFAULT_ASSET_TYPE;
    const horizon: AnalysisHorizon = body.horizon || DEFAULT_HORIZON;
    const skipCache = body.skipCache === true;

    if (!ticker) {
      return NextResponse.json({ error: 'Ticker symbol is required' }, { status: 400 });
    }

    if (!['equity', 'crypto', 'forex', 'etf', 'commodity'].includes(assetType)) {
      return NextResponse.json({ error: `Unsupported asset type: ${assetType}` }, { status: 400 });
    }

    if (!['1W', '1M', '3M', '6M', '1Y'].includes(horizon)) {
      return NextResponse.json({ error: `Unsupported horizon: ${horizon}` }, { status: 400 });
    }

    // Check for cached full response first (unless skipCache is set)
    const fullCacheKey = marketCache.generateKey('full-analysis', ticker, assetType, horizon);
    if (!skipCache) {
      const cachedResponse = marketCache.get<AnalyzerResponse>(fullCacheKey);
      if (cachedResponse) {
        console.log(`[API] Full cache hit for ${ticker} (${Date.now() - startTime}ms)`);
        return NextResponse.json({ 
          success: true, 
          data: cachedResponse,
          cached: true,
          timing: Date.now() - startTime,
        });
      }
    }

    const marketDataService = new MarketDataService();
    const newsService = new NewsService();
    const cortensorService = new CortensorService();

    // Fetch market data with caching
    const contextCacheKey = marketCache.generateKey('context', ticker, assetType, horizon);
    let context: MarketAnalysisContext;
    
    const cachedContext = skipCache ? null : marketCache.get<MarketAnalysisContext>(contextCacheKey);
    if (cachedContext) {
      console.log(`[API] Context cache hit for ${ticker}`);
      context = cachedContext;
    } else {
      context = await marketDataService.buildContext({ ticker, assetType, horizon });
      marketCache.set(contextCacheKey, context, ttlTypeForAsset(assetType));
    }

    // Fetch news with caching
    const newsCacheKey = marketCache.generateKey('news', ticker, assetType);
    const news = await marketCache.getOrFetch(
      newsCacheKey,
      () => newsService.fetchLatestNews({
        ticker,
        companyName: context.snapshot.companyName,
        assetType,
        horizon,
      }),
      'news',
    );

    const enrichedContext: MarketAnalysisContext = {
      ...context,
      news,
    };

    const ai = await cortensorService.generatePriceAnalysis(enrichedContext);

    const response: AnalyzerResponse = {
      meta: { ...enrichedContext.snapshot, horizon },
      technicals: enrichedContext.technicals,
      fundamentals: enrichedContext.fundamentals,
      history: enrichedContext.history,
      news,
      catalysts: enrichedContext.catalysts,
      ai,
    };

    // Cache the full response
    marketCache.set(fullCacheKey, response, ttlTypeForAsset(assetType));

    const timing = Date.now() - startTime;
    console.log(`[API] Analysis complete for ${ticker} (${timing}ms)`);

    return NextResponse.json({ 
      success: true, 
      data: response,
      cached: false,
      timing,
    });
  } catch (error) {
    if (error instanceof MarketDataError) {
      console.warn('Market data request rejected:', error.message);
      return NextResponse.json({ error: error.message, code: error.code ?? 'MARKET_DATA_ERROR' }, { status: error.status });
    }

    console.error('Price analyzer error:', error);
    return NextResponse.json({ error: 'Failed to process analysis request' }, { status: 500 });
  }
}
