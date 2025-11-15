import axios from 'axios';
import type { EnrichmentSource } from './cortensorService';

interface TavilyResult {
  title?: string;
  url: string;
  content?: string;
  snippet?: string;
}

interface TavilyResponse {
  results?: TavilyResult[];
}

interface GoogleSearchItem {
  title?: string;
  link: string;
  snippet?: string;
}

interface GoogleSearchResponse {
  items?: GoogleSearchItem[];
}

export class SearchService {
  private googleApiKey: string;
  private googleSearchEngineId: string;
  private tavilyApiKey: string;

  constructor() {
    this.googleApiKey = process.env.GOOGLE_API_KEY || '';
    this.googleSearchEngineId = process.env.GOOGLE_SEARCH_ENGINE_ID || '';
    this.tavilyApiKey = process.env.TAVILY_API_KEY || '';
  }

  async searchAdditionalSources(
    title: string,
    keywords: string[],
    originalUrl: string
  ): Promise<EnrichmentSource[]> {
    const sources: EnrichmentSource[] = [];
    
    // Priority 1: Tavily (Primary - Working and reliable)
    if (this.tavilyApiKey) {
      try {
        console.log('🔍 Searching with Tavily API (Primary search provider)...');
        const tavilySources = await this.searchWithTavily(title, keywords);
        sources.push(...tavilySources);
        console.log(`✅ Tavily successfully found ${tavilySources.length} relevant sources`);
      } catch (error) {
        console.warn('❌ Tavily search failed:', error);
      }
    }
    
    // Priority 2: Google Custom Search (Backup - if Tavily insufficient)
    if (this.googleApiKey && this.googleSearchEngineId && sources.length < 3) {
      try {
        console.log('🔍 Searching with Google Custom Search (Backup provider)...');
        const googleSources = await this.searchWithGoogle(title, keywords);
        if (googleSources.length > 0) {
          sources.push(...googleSources);
          console.log(`✅ Google successfully found ${googleSources.length} additional sources`);
        } else {
          console.log('⚠️ Google Custom Search returned no results (search engine configuration may be required)');
        }
      } catch (error) {
        console.warn('❌ Google search failed:', error);
      }
    }
    
    // Fallback: Use broader search terms if no sources found
    if (sources.length === 0) {
      console.log('🔍 Attempting fallback search with broader terms...');
      return this.fallbackSearch(title, originalUrl);
    }
    
    // Filter out the original URL and deduplicate
    const filteredSources = this.deduplicateSources(
      sources.filter(source => source.url !== originalUrl)
    ).slice(0, 5); // Limit to 5 sources
    
    console.log(`📋 Search completed: ${filteredSources.length} unique, relevant sources found for enhancement`);
    return filteredSources;
  }

  private async searchWithTavily(
    title: string,
    keywords: string[]
  ): Promise<EnrichmentSource[]> {
    try {
      const query = this.buildSearchQuery(title, keywords);
      
      const response = await axios.post<TavilyResponse>(
        'https://api.tavily.com/search',
        {
          api_key: this.tavilyApiKey,
          query,
          search_depth: 'basic',
          include_images: false,
          include_answer: false,
          max_results: 5
        },
        {
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      if (response.data && response.data.results) {
        return response.data.results.map((result: TavilyResult) => ({
          title: result.title || 'Untitled',
          url: result.url,
          snippet: result.content || result.snippet || ''
        }));
      }

      return [];
    } catch (error) {
      console.error('Tavily search error:', error);
      return [];
    }
  }

  private async searchWithGoogle(
    title: string,
    keywords: string[]
  ): Promise<EnrichmentSource[]> {
    try {
      const query = this.buildSearchQuery(title, keywords);
      
      const response = await axios.get<GoogleSearchResponse>(
        'https://www.googleapis.com/customsearch/v1',
        {
          params: {
            key: this.googleApiKey,
            cx: this.googleSearchEngineId,
            q: query,
            num: 5,
            safe: 'active'
          }
        }
      );

      if (response.data && response.data.items) {
        return response.data.items.map((item: GoogleSearchItem) => ({
          title: item.title || 'Untitled',
          url: item.link,
          snippet: item.snippet || ''
        }));
      }

      return [];
    } catch (error) {
      console.error('Google search error:', error);
      return [];
    }
  }

  private async fallbackSearch(title: string, originalUrl: string): Promise<EnrichmentSource[]> {
    // Extract broad topic from title for fallback search
    const broadTerms = title
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length > 4 && !['article', 'news', 'post', 'blog'].includes(word))
      .slice(0, 2);
    
    if (broadTerms.length === 0) {
      console.log('⚠️ No suitable fallback terms found for broader search');
      return [];
    }
    
    // Try Tavily with broader search terms
    if (this.tavilyApiKey) {
      try {
        const fallbackQuery = broadTerms.join(' OR ');
        console.log(`🔍 Executing fallback Tavily search with query: "${fallbackQuery}"`);
        
        const response = await axios.post<TavilyResponse>(
          'https://api.tavily.com/search',
          {
            api_key: this.tavilyApiKey,
            query: fallbackQuery,
            search_depth: 'basic',
            include_images: false,
            include_answer: false,
            max_results: 3
          },
          {
            headers: {
              'Content-Type': 'application/json'
            }
          }
        );

        if (response.data && response.data.results) {
          const fallbackSources = response.data.results
            .filter((result: TavilyResult) => result.url !== originalUrl)
            .map((result: TavilyResult) => ({
              title: result.title || 'Related Article',
              url: result.url,
              snippet: result.content || result.snippet || ''
            }));
          
          console.log(`✅ Fallback search successfully found ${fallbackSources.length} relevant sources`);
          return fallbackSources;
        }
      } catch (error) {
        console.error('❌ Fallback search failed:', error);
      }
    }
    
    return [];
  }

  private buildSearchQuery(title: string, keywords: string[]): string {
    // Extract key terms from title and keywords
    const titleWords = title
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length > 3)
      .slice(0, 3);

    // Combine title words with extracted keywords
    const searchTerms = [...titleWords, ...keywords.slice(0, 3)];
    
    // Remove duplicates and create search query
    const uniqueTerms = Array.from(new Set(searchTerms));
    return uniqueTerms.join(' ');
  }

  private deduplicateSources(sources: EnrichmentSource[]): EnrichmentSource[] {
    const seen = new Set<string>();
    return sources.filter(source => {
      const key = source.url.toLowerCase();
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }

  extractKeywords(content: string): string[] {
    // Professional keyword extraction algorithm
    const words = content
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => 
        word.length >= 4 && 
        !this.isStopWord(word) &&
        !word.match(/^\d+$/) // Exclude pure numbers
      );

    // Calculate word frequency
    const frequency: Record<string, number> = {};
    words.forEach(word => {
      frequency[word] = (frequency[word] || 0) + 1;
    });

    // Sort by frequency and return top keywords
    return Object.entries(frequency)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([word]) => word);
  }

  private isStopWord(word: string): boolean {
    const stopWords = new Set([
      'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 
      'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 
      'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'that',
      'with', 'have', 'this', 'will', 'your', 'from', 'they', 'know', 'want', 'been', 'good', 
      'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 
      'many', 'over', 'such', 'take', 'than', 'them', 'well', 'were', 'what'
    ]);
    return stopWords.has(word);
  }
}
