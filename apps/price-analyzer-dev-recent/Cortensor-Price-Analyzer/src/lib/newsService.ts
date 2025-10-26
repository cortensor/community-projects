import axios from 'axios';
import type { AnalysisHorizon, AssetType, MarketNewsItem } from './marketTypes';

interface NewsApiArticle {
  title?: string;
  description?: string;
  url?: string;
  source?: { name?: string };
  publishedAt?: string;
}

interface TavilyArticle {
  title?: string;
  content?: string;
  snippet?: string;
  url?: string;
  source?: string;
  published_date?: string;
  publishedAt?: string;
}

interface GoogleSearchItem {
  title?: string;
  snippet?: string;
  link?: string;
  displayLink?: string;
  pagemap?: { metatags?: Array<Record<string, string | undefined>> };
}

interface FetchNewsParams {
  ticker: string;
  companyName?: string;
  assetType: AssetType;
  horizon: AnalysisHorizon;
}

export class NewsService {
  private newsApiKey = process.env.NEWS_API_KEY;
  private tavilyApiKey = process.env.TAVILY_API_KEY;
  private googleApiKey = process.env.GOOGLE_API_KEY;
  private googleSearchEngineId = process.env.GOOGLE_SEARCH_ENGINE_ID;

  async fetchLatestNews(params: FetchNewsParams): Promise<MarketNewsItem[]> {
    const news: MarketNewsItem[] = [];

    if (this.newsApiKey) {
      try {
        const articles = await this.fetchFromNewsApi(params);
        news.push(...articles);
      } catch (error) {
        console.warn('NewsAPI fetch failed:', error);
      }
    }

    if (news.length < 3 && this.tavilyApiKey) {
      try {
        const tavilyArticles = await this.fetchFromTavily(params);
        news.push(...tavilyArticles);
      } catch (error) {
        console.warn('Tavily news fetch failed:', error);
      }
    }

    if (news.length < 3 && this.googleApiKey && this.googleSearchEngineId) {
      try {
        const googleArticles = await this.fetchFromGoogle(params);
        news.push(...googleArticles);
      } catch (error) {
        console.warn('Google Custom Search news fetch failed:', error);
      }
    }

    return this.deduplicate(news).slice(0, 6);
  }

  private async fetchFromNewsApi(params: FetchNewsParams): Promise<MarketNewsItem[]> {
    const queryParts = [params.ticker];
    if (params.companyName) {
      queryParts.push(`"${params.companyName}"`);
    }

    const query = queryParts.join(' OR ');
    const response = await axios.get<{ articles?: NewsApiArticle[] }>('https://newsapi.org/v2/everything', {
      params: {
        q: query,
        pageSize: 10,
        sortBy: 'publishedAt',
        language: 'en',
        apiKey: this.newsApiKey,
      },
    });

    const articles = response.data?.articles ?? [];
    return articles.map((article) => this.toNewsItem({
      title: article.title,
      description: article.description,
      url: article.url,
      source: article.source?.name,
      publishedAt: article.publishedAt,
    }));
  }

  private async fetchFromTavily(params: FetchNewsParams): Promise<MarketNewsItem[]> {
    const response = await axios.post<{ results?: TavilyArticle[] }>('https://api.tavily.com/search', {
      api_key: this.tavilyApiKey,
      query: `${params.ticker} ${params.companyName || ''} latest market news`,
      search_depth: 'basic',
      include_images: false,
      include_answer: false,
      max_results: 5,
    });

    const results = response.data?.results ?? [];
    return results.map((result) => this.toNewsItem({
      title: result.title,
      description: result.content || result.snippet,
      url: result.url,
      source: result.source || 'Tavily',
      publishedAt: result.published_date || result.publishedAt,
    }));
  }

  private async fetchFromGoogle(params: FetchNewsParams): Promise<MarketNewsItem[]> {
    const response = await axios.get<{ items?: GoogleSearchItem[] }>('https://www.googleapis.com/customsearch/v1', {
      params: {
        key: this.googleApiKey,
        cx: this.googleSearchEngineId,
        q: `${params.ticker} ${params.companyName || ''} stock`,
        num: 5,
        dateRestrict: 'd7',
      },
    });

    const items = response.data?.items ?? [];
    return items.map((item) => this.toNewsItem({
      title: item.title,
      description: item.snippet,
      url: item.link,
      source: item.displayLink,
      publishedAt: item.pagemap?.metatags?.[0]?.['article:published_time'] || new Date().toISOString(),
    }));
  }

  private deduplicate(items: MarketNewsItem[]): MarketNewsItem[] {
    const seen = new Set<string>();
    const deduped: MarketNewsItem[] = [];

    items.forEach((item) => {
      const key = item.url.toLowerCase();
      if (!seen.has(key)) {
        seen.add(key);
        deduped.push(item);
      }
    });

    return deduped;
  }

  private toNewsItem(item: { title?: string; description?: string; url?: string; source?: string; publishedAt?: string }): MarketNewsItem {
    return {
      title: item.title?.trim() || 'Untitled headline',
      url: item.url || '#',
      source: item.source || 'Unknown',
      summary: item.description?.trim(),
      publishedAt: item.publishedAt ? new Date(item.publishedAt).toISOString() : new Date().toISOString(),
      sentiment: this.estimateSentiment(`${item.title} ${item.description}`),
    };
  }

  private estimateSentiment(text?: string): 'positive' | 'neutral' | 'negative' {
    if (!text) return 'neutral';
    const lower = text.toLowerCase();

    const positiveKeywords = ['beats', 'growth', 'surge', 'record', 'upgrade', 'outperform', 'strong', 'positive'];
    const negativeKeywords = ['misses', 'fall', 'plunge', 'downgrade', 'lawsuit', 'weak', 'negative', 'regulatory'];

    const positive = positiveKeywords.some((keyword) => lower.includes(keyword));
    const negative = negativeKeywords.some((keyword) => lower.includes(keyword));

    if (positive && !negative) return 'positive';
    if (negative && !positive) return 'negative';
    return 'neutral';
  }
}

export type { FetchNewsParams };
