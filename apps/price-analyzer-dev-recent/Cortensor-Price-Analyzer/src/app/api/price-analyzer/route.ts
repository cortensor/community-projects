import { NextRequest, NextResponse } from 'next/server';
import { MarketDataService } from '@/lib/marketDataService';
import { NewsService } from '@/lib/newsService';
import { CortensorService } from '@/lib/cortensorService';
import type { AnalysisHorizon, AnalyzerResponse, AssetType, MarketAnalysisContext } from '@/lib/marketTypes';

interface AnalyzerRequestBody {
  ticker?: string;
  assetType?: AssetType;
  horizon?: AnalysisHorizon;
}

const DEFAULT_ASSET_TYPE: AssetType = 'equity';
const DEFAULT_HORIZON: AnalysisHorizon = '3M';

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as AnalyzerRequestBody;
    const ticker = body.ticker?.trim().toUpperCase();
    const assetType: AssetType = body.assetType || DEFAULT_ASSET_TYPE;
    const horizon: AnalysisHorizon = body.horizon || DEFAULT_HORIZON;

    if (!ticker) {
      return NextResponse.json({ error: 'Ticker symbol is required' }, { status: 400 });
    }

    if (!['equity', 'crypto', 'forex', 'etf', 'commodity'].includes(assetType)) {
      return NextResponse.json({ error: `Unsupported asset type: ${assetType}` }, { status: 400 });
    }

    if (!['1W', '1M', '3M', '6M', '1Y'].includes(horizon)) {
      return NextResponse.json({ error: `Unsupported horizon: ${horizon}` }, { status: 400 });
    }

    const marketDataService = new MarketDataService();
    const newsService = new NewsService();
    const cortensorService = new CortensorService();

    const context = await marketDataService.buildContext({ ticker, assetType, horizon });

    const news = await newsService.fetchLatestNews({
      ticker,
      companyName: context.snapshot.companyName,
      assetType,
      horizon,
    });

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

    return NextResponse.json({ success: true, data: response });
  } catch (error) {
    console.error('Price analyzer error:', error);
    return NextResponse.json({ error: 'Failed to process analysis request' }, { status: 500 });
  }
}
