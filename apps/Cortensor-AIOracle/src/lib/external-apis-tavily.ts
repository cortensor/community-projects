// Tavily AI Search - Primary source for fact-checking and real-time data

interface TavilyResult {
  title: string
  url: string
  content: string
  score: number
  published_date?: string
}

interface TavilyResponse {
  results: TavilyResult[]
  query: string
  response_time: number
}

interface SourceArticle {
  title: string
  url: string
  reliability: string
  snippet?: string
  domain?: string
  publishedAt?: string
  publisher?: string
}

export class TavilyDataService {
  private static readonly TAVILY_API_KEY = process.env.TAVILY_API_KEY
  private static readonly TAVILY_BASE_URL = 'https://api.tavily.com'
  
  /**
   * Search using Tavily AI - Returns high-quality, credible sources
   * @param query - Search query
   * @param options - Search options (max_results, search_depth, include_domains, exclude_domains)
   */
  static async search(
    query: string, 
    options: {
      maxResults?: number
      searchDepth?: 'basic' | 'advanced'
      includeDomains?: string[]
      excludeDomains?: string[]
      includeAnswer?: boolean
    } = {}
  ): Promise<{ sources: SourceArticle[], answer?: string }> {
    if (!this.TAVILY_API_KEY) {
      console.warn('[Tavily] API key not configured')
      return { sources: [] }
    }

    try {
      const response = await fetch(`${this.TAVILY_BASE_URL}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.TAVILY_API_KEY}`
        },
        body: JSON.stringify({
          query,
          max_results: options.maxResults || 5,
          search_depth: options.searchDepth || 'advanced',
          include_domains: options.includeDomains || [],
          exclude_domains: options.excludeDomains || [],
          include_answer: options.includeAnswer !== false,
          include_raw_content: false,
          include_images: false
        })
      })

      if (!response.ok) {
        console.error('[Tavily] API error:', response.status, response.statusText)
        return { sources: [] }
      }

      const data: TavilyResponse & { answer?: string } = await response.json()
      
      // Transform Tavily results to our SourceArticle format
      const sources: SourceArticle[] = data.results.map(result => {
        const domain = this.extractDomain(result.url)
        const reliability = this.assessReliability(domain, result.score)
        
        return {
          title: result.title,
          url: result.url,
          reliability,
          snippet: result.content.slice(0, 200) + (result.content.length > 200 ? '...' : ''),
          domain,
          publishedAt: result.published_date || new Date().toISOString(),
          publisher: this.getDomainName(domain)
        }
      })

      console.log(`[Tavily] Found ${sources.length} sources for query: "${query}"`)

      return {
        sources: sources.slice(0, options.maxResults || 5),
        answer: data.answer
      }

    } catch (error) {
      console.error('[Tavily] Search error:', error)
      return { sources: [] }
    }
  }

  /**
   * Get sources for fact-checking claims
   * Uses advanced search depth and prefers fact-checking domains
   */
  static async getFactCheckSources(claim: string): Promise<SourceArticle[]> {
    const factCheckDomains = [
      'snopes.com',
      'factcheck.org',
      'politifact.com',
      'fullfact.org',
      'apnews.com',
      'reuters.com',
      'bbc.com',
      'who.int',
      'cdc.gov',
      'nih.gov',
      'nasa.gov'
    ]

    const result = await this.search(claim, {
      maxResults: 5,
      searchDepth: 'advanced',
      includeDomains: factCheckDomains
    })

    return result.sources
  }

  /**
   * Backward compatibility - get fact checks
   */
  static async getFactChecks(query: string): Promise<any[]> {
    const sources = await this.getFactCheckSources(query)
    return sources.map(s => ({
      text: s.snippet || '',
      url: s.url,
      title: s.title,
      publisher: s.publisher || s.domain,
      publishedAt: s.publishedAt
    }))
  }

  /**
   * Enrich query with external data - main method for oracle-engine
   */
  static async enrichQueryWithExternalData(query: string): Promise<string> {
    const sources = await getRelevantArticles(query)
    
    if (sources.length === 0) {
      return 'No recent sources found.'
    }

    // Format sources as context
    let context = 'REAL-TIME DATA SOURCES:\n\n'
    sources.forEach((source, i) => {
      context += `${i + 1}. ${source.title}\n`
      context += `   Source: ${source.publisher || source.domain} (${source.reliability} credibility)\n`
      if (source.snippet) {
        context += `   ${source.snippet}\n`
      }
      context += `   URL: ${source.url}\n\n`
    })

    return context
  }

  /**
   * Extract domain from URL
   */
  private static extractDomain(url: string): string {
    try {
      const urlObj = new URL(url)
      return urlObj.hostname.replace(/^www\./, '')
    } catch {
      return 'unknown'
    }
  }

  /**
   * Get readable domain name
   */
  private static getDomainName(domain: string): string {
    const parts = domain.split('.')
    if (parts.length >= 2) {
      return parts[parts.length - 2].charAt(0).toUpperCase() + parts[parts.length - 2].slice(1)
    }
    return domain
  }

  /**
   * Assess source reliability based on domain and score
   */
  private static assessReliability(domain: string, score: number): string {
    // High credibility domains
    const highCredibility = [
      'gov', 'edu', 'who.int', 'cdc.gov', 'nih.gov', 'nasa.gov',
      'reuters.com', 'apnews.com', 'bbc.com', 'bbc.co.uk',
      'nature.com', 'science.org', 'sciencedirect.com',
      'snopes.com', 'factcheck.org', 'politifact.com', 'fullfact.org'
    ]

    const isTrustedDomain = highCredibility.some(trusted => 
      domain.endsWith(trusted) || domain.includes(trusted)
    )

    if (isTrustedDomain && score >= 0.7) return 'High'
    if (isTrustedDomain || score >= 0.8) return 'High'
    if (score >= 0.6) return 'Medium'
    return 'Low'
  }
}

/**
 * Main function to get sources for any query
 * This replaces the old ExternalDataService.enrichQueryWithExternalData
 */
export async function getRelevantArticles(query: string): Promise<SourceArticle[]> {
  // Check if it's a fact-check query
  const isFactCheck = /is it true|is this true|correct|real|hoax|myth|fact.?check|claim/i.test(query)
  
  if (isFactCheck) {
    return await TavilyDataService.getFactCheckSources(query)
  }

  // Regular search
  const result = await TavilyDataService.search(query, {
    maxResults: 5,
    searchDepth: 'advanced'
  })

  return result.sources
}

// Export for backward compatibility
export { TavilyDataService as ExternalDataService }
