// External API integrations for real-time data
interface NewsArticle {
  title: string
  description: string
  url: string
  publishedAt: string
  source: {
    name: string
  }
}

interface CryptoPrice {
  id: string
  symbol: string
  name: string
  current_price: number
  price_change_percentage_24h: number
  market_cap: number
  last_updated: string
}

interface StockPrice {
  symbol: string
  price: number
  change: number
  changePercent: number
  marketCap?: number
  volume?: number
}

interface WeatherData {
  location: string
  temperature: number
  condition: string
  humidity: number
  windSpeed: number
}

export class ExternalDataService {
  private static readonly NEWS_API_KEY = process.env.NEWS_API_KEY
  private static readonly GUARDIAN_API_KEY = process.env.GUARDIAN_API_KEY
  // Currents and GNews disabled per configuration
  // private static readonly CURRENTS_API_KEY = process.env.CURRENTS_API_KEY
  // private static readonly GNEWS_API_KEY = process.env.GNEWS_API_KEY
  private static readonly GOOGLE_FACTCHECK_API_KEY = process.env.GOOGLE_FACTCHECK_API_KEY
  private static readonly ALPHA_VANTAGE_KEY = process.env.ALPHA_VANTAGE_API_KEY
  private static readonly WEATHER_API_KEY = process.env.WEATHER_API_KEY
  private static readonly COINGECKO_API_KEY = process.env.COINGECKO_API_KEY
  private static readonly FASTFOREX_API_KEY = process.env.FASTFOREX_API_KEY
  private static readonly VALIDATE_LINKS = (process.env.VALIDATE_SOURCE_LINKS || 'true').toLowerCase() !== 'false'
  private static readonly FREE_ONLY = (process.env.FREE_SOURCES_ONLY || 'true').toLowerCase() !== 'false'
  private static readonly WEB_SEARCH_ENABLED = (process.env.WEB_SEARCH_ENABLED || 'true').toLowerCase() !== 'false'
  private static readonly WEB_SCRAPE_ENABLED = (process.env.WEB_SCRAPE_ENABLED || 'true').toLowerCase() !== 'false'
  private static readonly RSS_HL = process.env.NEWS_RSS_HL || 'en-US'
  private static readonly RSS_GL = process.env.NEWS_RSS_GL || 'US'
  private static readonly RSS_CEID = process.env.NEWS_RSS_CEID || 'US:en'

  // Simple in-memory caches with TTL to reduce network calls
  private static readonly headCache: Map<string, { url: string; expiry: number }> = new Map()
  private static readonly metaCache: Map<string, { data: { description?: string; publisher?: string; publishedAt?: string } | null; expiry: number }> = new Map()

  // Helpers: URL normalization and deep-link scoring
  private static normalizeUrl(raw: string): string {
    let u = raw.trim().replace(/[)\]\.,;:'"\s]+$/g, '')
    try {
      const urlObj = new URL(u)
      const toDelete: string[] = []
      urlObj.searchParams.forEach((_, k) => {
        if (/^utm_|^ref$|^fbclid$|^gclid$|^mc_cid$|^mc_eid$/i.test(k)) toDelete.push(k)
      })
      toDelete.forEach(k => urlObj.searchParams.delete(k))
      urlObj.hash = ''
      return urlObj.toString()
    } catch { return u }
  }

  private static deepScore(u: string): number {
    try {
      const { pathname } = new URL(u)
      const parts = pathname.split('/').filter(Boolean)
      const depth = parts.length
      const hasSlug = parts.some(p => /[a-z0-9-]{6,}/i.test(p))
      const hasDate = /(19|20)\d{2}\/(0?[1-9]|1[0-2])\//.test(pathname)
      return (depth >= 2 ? 2 : depth >= 1 ? 1 : 0) + (hasSlug ? 1 : 0) + (hasDate ? 1 : 0)
    } catch { return 0 }
  }

  // Paths like /tag/, /topic/, /search, /news (root), or shallow index-like pages
  private static isAggregatorOrHomepage(u: string): boolean {
    try {
      const url = new URL(u)
      const host = url.hostname.replace(/^www\./, '')
      const path = url.pathname.replace(/\/+$/, '').toLowerCase()
      if (!path || path === '/' || path === '/en' || path === '/news') return true
      const badSegments = ['tag', 'tags', 'topic', 'topics', 'search', 'section', 'sections', 'category', 'categories', 'channel', 'channels']
      const parts = path.split('/').filter(Boolean)
      if (parts.length <= 1 && /(news|berita|latest|top-stories)$/i.test(parts[0] || '')) return true
      if (parts.some(p => badSegments.includes(p))) return true
      // Explicitly treat Google News host as aggregator
      if (/(^|\.)news\.google\.com$/i.test(host)) return true
      return false
    } catch { return false }
  }

  // Check if URL likely points to an article (not a hub/home/search page)
  private static looksLikeArticle(u: string): boolean {
    try {
      const score = this.deepScore(u)
      if (score >= 2) return true
      const { pathname } = new URL(u)
      const parts = pathname.split('/').filter(Boolean)
      const hasSlug = parts.some(p => /[a-z0-9-]{8,}/i.test(p))
      return hasSlug && parts.length >= 2
    } catch { return false }
  }

  private static isGenericSnippet(snippet?: string, title?: string): boolean {
    if (!snippet) return true
    const s = snippet.replace(/<[^>]+>/g, '').trim().toLowerCase()
    if (!s) return true
    const t = (title || '').trim().toLowerCase()
    const genericPatterns = [
      /comprehensive\s+up-to-date\s+news\s+coverage[\s\S]*google\s+news/i,
      /aggregated\s+from\s+sources\s+all\s+over\s+the\s+world/i,
      /^google\s+news$/i
    ]
    if (genericPatterns.some(r => r.test(s))) return true
    if (t && (s === t || (s.includes(t) && Math.abs(s.length - t.length) < 10))) return true
    const words = s.split(/\s+/).filter(Boolean)
    if (s.length < 40 || words.length < 8) return true
    return false
  }

  private static keywordsFromQuery(query: string): string[] {
    const stop = new Set(['the','a','an','of','to','in','on','for','and','or','is','are','was','were','with','by','about','latest','news','today','recent'])
    return query
      .toLowerCase()
      .replace(/[^a-z0-9\s-]+/g, ' ')
      .split(/\s+/)
      .filter(w => w && !stop.has(w) && w.length >= 3)
      .slice(0, 8)
  }

  // Detect simple claim-style queries that benefit from fact-check sources first
  private static isClaimQuery(query: string): boolean {
  const q = query.toLowerCase().trim()
  // Common claim/question forms + health/science triggers
  const questionLead = /^(can|does|do|is|are|will|should|did|has|have|was|were)\b/.test(q)
  const claimWords = /(is it true|is this true|correct|real|really|hoax|myth|fact[- ]?check|claim|klaim|benarkah|apakah benar)/.test(q)
  const classicPhrases = /(visible from space|flat earth|cure|prevent|treat|kill|eliminate|reduce risk)/.test(q)
  const healthContext = /(covid|coronavirus|sars-cov-2|virus|vaccine|hot water|drinking hot water|garlic|sunlight|steam)/.test(q)
  return claimWords || classicPhrases || (questionLead && (healthContext || /did\s+\w+/.test(q)))
  }

  private static isRelevant(title: string, description: string | undefined, query: string): boolean {
    const keys = this.keywordsFromQuery(query)
    if (keys.length === 0) return true
    const t = (title || '').toLowerCase()
    const d = (description || '').toLowerCase()
    // Require at least one keyword in title or description
    return keys.some(k => t.includes(k) || d.includes(k))
  }

  private static isUtilityHomepage(u: string): boolean {
    try {
      const url = new URL(u)
      const host = url.hostname.replace(/^www\./, '')
      const path = url.pathname.replace(/\/+$/, '')
      const shallow = path === '' || path === '/' || path === '/en' || path === '/news'
      const utilityHosts = /(coingecko\.com|x-rates\.com|investing\.com|yahoo\.com|ft\.com)$/i
      return shallow && utilityHosts.test(host)
    } catch { return false }
  }

  private static async resolveUrlWithHead(u: string): Promise<string> {
  // Skip HEAD requests entirely when scraping disabled or validation disabled
  if (!this.WEB_SCRAPE_ENABLED || !this.VALIDATE_LINKS) return u
  // Serve from cache if fresh (1 hour TTL)
  const now = Date.now()
  const cached = this.headCache.get(u)
  if (cached && cached.expiry > now) return cached.url
    try {
      const controller = new AbortController()
      const id = setTimeout(() => controller.abort(), 3000)
      const resp = await fetch(u, { method: 'HEAD', redirect: 'follow', signal: controller.signal })
      clearTimeout(id)
      if (resp && (resp.ok || (resp.status >= 200 && resp.status < 400))) {
    const finalUrl = resp.url || u
    this.headCache.set(u, { url: finalUrl, expiry: now + 60 * 60 * 1000 })
    return finalUrl
      }
    } catch {}
  this.headCache.set(u, { url: u, expiry: Date.now() + 15 * 60 * 1000 })
    return u
  }

  // Google News RSS fallback (no API key required)
  private static async googleNewsRSS(query: string, options?: { max?: number }): Promise<NewsArticle[]> {
  if (!this.WEB_SEARCH_ENABLED) return []
    try {
      const max = options?.max ?? 10
      const url = `https://news.google.com/rss/search?q=${encodeURIComponent(query)}&hl=${encodeURIComponent(this.RSS_HL)}&gl=${encodeURIComponent(this.RSS_GL)}&ceid=${encodeURIComponent(this.RSS_CEID)}`
      const resp = await fetch(url, { headers: { 'Accept': 'application/rss+xml, application/xml, text/xml' } })
      if (!resp.ok) throw new Error(`Google RSS error: ${resp.status}`)
      const xml = await resp.text()
      // naive parsing of <item> blocks
      const items = Array.from(xml.matchAll(/<item>([\s\S]*?)<\/item>/g)).slice(0, max)
      const out: NewsArticle[] = []
      for (const m of items) {
        const block = m[1]
        const title = (block.match(/<title><!\[CDATA\[(.*?)\]\]><\/title>/)?.[1]
          || block.match(/<title>(.*?)<\/title>/)?.[1]
          || '').trim()
        const linkRaw = (block.match(/<link>(.*?)<\/link>/)?.[1] || '').trim()
        // Prefer original publisher link inside description's anchor if present
        const descCdata = block.match(/<description><!\[CDATA\[([\s\S]*?)\]\]><\/description>/)
        const descPlain = descCdata ? descCdata[1] : (block.match(/<description>([\s\S]*?)<\/description>/)?.[1] || '')
        const anchorHref = descPlain.match(/<a[^>]+href="([^"]+)"/i)?.[1]
        const linkCandidate = anchorHref || linkRaw
        const publishedAt = (block.match(/<pubDate>(.*?)<\/pubDate>/)?.[1] || new Date().toISOString()).toString()
        const sourceName = (block.match(/<source[^>]*>(.*?)<\/source>/)?.[1] || 'Google News')
        const cleaned = this.normalizeUrl(linkCandidate)
        const resolved = await this.resolveUrlWithHead(cleaned)
        // Skip aggregators/homepages and Google News hosts
        if (this.isAggregatorOrHomepage(resolved)) continue
        const decode = (s: string) => s
          .replace(/&amp;/g, '&')
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
          .replace(/&quot;/g, '"')
          .replace(/&#39;/g, "'")
        // Build a readable snippet from description (strip tags)
        const snippetHtml = descPlain || ''
        const snippetText = decode(snippetHtml.replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim()
        const meta = await this.fetchMetaQuick(resolved)
        const finalTitle = title || resolved
        const finalDesc = (meta?.description || snippetText || title)
        if (!this.looksLikeArticle(resolved)) continue
        if (!this.isRelevant(finalTitle, finalDesc, query)) continue
        if (this.isGenericSnippet(finalDesc, finalTitle)) {
          // Try to recover via metadata; if still generic, skip
          if (!meta || this.isGenericSnippet(meta.description, finalTitle)) continue
        }
        out.push({
          title: finalTitle,
          description: finalDesc,
          url: resolved,
          publishedAt: (meta?.publishedAt || new Date(publishedAt).toISOString()),
          source: { name: (meta?.publisher || sourceName) }
        })
      }
      return out
    } catch (e) {
      console.error('Error fetching Google News RSS:', e)
      return []
    }
  }

  // Fetch basic metadata (description, publisher, date) from an article URL
  private static async fetchMetaQuick(url: string): Promise<{ description?: string; publisher?: string; publishedAt?: string } | null> {
  // Disable HTML fetching/scraping when WEB_SCRAPE_ENABLED is false
  if (!this.WEB_SCRAPE_ENABLED) return null
    try {
  // Cache (15 minutes TTL)
  const now = Date.now()
  const cached = this.metaCache.get(url)
  if (cached && cached.expiry > now) return cached.data
      const controller = new AbortController()
      const id = setTimeout(() => controller.abort(), 3500)
      const res = await fetch(url, { method: 'GET', redirect: 'follow', signal: controller.signal, headers: { 'Accept': 'text/html,application/xhtml+xml' } })
      clearTimeout(id)
      if (!res.ok) return null
      const html = await res.text()
      const meta = (name: string, prop?: 'name' | 'property') => {
        const re = new RegExp(`<meta[^>]+${prop || 'name'}=["']${name}["'][^>]*content=["']([^"']+)["'][^>]*>`, 'i')
        return html.match(re)?.[1]
      }
      const ogDesc = meta('og:description', 'property')
      const desc = ogDesc || meta('description') || undefined
      const site = meta('og:site_name', 'property') || undefined
      const artTime = meta('article:published_time', 'property') || meta('og:updated_time', 'property') || undefined
  const out = { description: desc, publisher: site, publishedAt: artTime }
  this.metaCache.set(url, { data: out, expiry: now + 15 * 60 * 1000 })
  return out
    } catch {
  this.metaCache.set(url, { data: null, expiry: Date.now() + 5 * 60 * 1000 })
  return null
    }
  }

  // The Guardian Open Platform
  private static async guardianSearch(
    query: string,
    max: number = 10,
    options?: { fromDate?: string; toDate?: string; pageSize?: number }
  ): Promise<NewsArticle[]> {
  if (!this.WEB_SEARCH_ENABLED) return []
    if (!this.GUARDIAN_API_KEY) return []
    try {
      // Build base URL with required params
      const pageSize = Math.max(1, Math.min(options?.pageSize ?? max, 50))
      const params: Record<string, string> = {
        q: query,
        'query-fields': 'headline', // improve topicality
        'show-fields': 'all',
        'page-size': String(pageSize),
        'order-by': 'newest',
        'api-key': this.GUARDIAN_API_KEY!
      }
      if (options?.fromDate) params['from-date'] = options.fromDate
      if (options?.toDate) params['to-date'] = options.toDate

      const out: NewsArticle[] = []
      let page = 1
      const mkUrl = () => {
        const usp = new URLSearchParams()
        for (const [k, v] of Object.entries(params)) usp.set(k, v)
        usp.set('page', String(page))
        return `https://content.guardianapis.com/search?${usp.toString()}`
      }

      while (out.length < max) {
        const url = mkUrl()
        const res = await fetch(url)
        if (!res.ok) {
          let body = ''
          try { body = await res.text() } catch {}
          console.error(`Guardian API error: ${res.status}`, body.slice(0, 500))
          // Stop on auth/rate limit errors to avoid loops
          if (res.status === 401 || res.status === 403 || res.status === 429) break
          break
        }
        const data = await res.json()
        const response = data?.response
        const results = response?.results || []
        for (const r of results) {
          const webUrl = this.normalizeUrl(r.webUrl)
          if (this.isAggregatorOrHomepage(webUrl)) continue
          const meta = await this.fetchMetaQuick(webUrl)
          const title = r.webTitle || webUrl
          // Prefer concise snippet from fields; fallback to meta description
          const rawBody = r.fields?.trailText || r.fields?.standfirst || r.fields?.headline || r.fields?.bodyText || ''
          const snippet = typeof rawBody === 'string' ? rawBody : ''
          const desc = (snippet && snippet.length > 0 ? snippet : (meta?.description || ''))
          // Stricter relevance for Guardian
          const keys = this.keywordsFromQuery(query)
          const titleLower = (title || '').toLowerCase()
          const descLower = (desc || '').toLowerCase()
          const hitsInTitle = keys.filter(k => titleLower.includes(k)).length
          const totalHits = keys.filter(k => titleLower.includes(k) || descLower.includes(k)).length
          if (!this.looksLikeArticle(webUrl)) continue
          if (this.isGenericSnippet(desc, title)) continue
          if (!(totalHits >= 2 && hitsInTitle >= 1)) continue
          out.push({
            title,
            description: desc,
            url: webUrl,
            publishedAt: (meta?.publishedAt || r.webPublicationDate || new Date().toISOString()),
            source: { name: meta?.publisher || 'The Guardian' }
          })
          if (out.length >= max) break
        }
        const totalPages = Number(response?.pages || 1)
        const currentPage = Number(response?.currentPage || page)
        if (out.length >= max || currentPage >= totalPages) break
        page = currentPage + 1
      }
      return out
    } catch (e) {
      console.error('Guardian search failed:', e)
      return []
    }
  }


  // Google Fact Check Tools API
  private static async googleFactCheck(query: string, max: number = 10): Promise<Array<{ title: string; url: string; publisher?: string; publishedAt?: string; rating?: string; snippet?: string }>> {
  if (!this.WEB_SEARCH_ENABLED) return []
    if (!this.GOOGLE_FACTCHECK_API_KEY) return []
    try {
      const url = `https://factchecktools.googleapis.com/v1alpha1/claims:search?query=${encodeURIComponent(query)}&pageSize=${max}&key=${this.GOOGLE_FACTCHECK_API_KEY}`
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Google FactCheck API error: ${res.status}`)
      const data = await res.json()
      const claims = data?.claims || []
      const out: Array<{ title: string; url: string; publisher?: string; publishedAt?: string; rating?: string; snippet?: string }> = []
      for (const c of claims) {
        const claim = c.claimReview?.[0]
        if (!claim) continue
        const title = claim.title || c.text || 'Fact check'
        const url = claim.url
        const publisher = claim.publisher?.name
        const publishedAt = claim.reviewDate
        const rating = claim.textualRating
        const snippet = c.claimant || c.text
        if (!url) continue
        out.push({ title, url, publisher, publishedAt, rating, snippet })
      }
      // Deduplicate by URL
      const seen = new Set<string>()
      return out.filter(i => { if (seen.has(i.url)) return false; seen.add(i.url); return true }).slice(0, max)
    } catch (e) {
      console.error('Google FactCheck fetch failed:', e)
      return []
    }
  }

  // News API - International news
  static async getLatestNews(query?: string, category?: string): Promise<NewsArticle[]> {
    try {
  if (!this.WEB_SEARCH_ENABLED) return []
  if (this.FREE_ONLY) return []
      if (!this.NEWS_API_KEY) {
        console.log('News API key not configured')
        return []
      }

      let url = 'https://newsapi.org/v2/top-headlines?'
      
      if (query) {
        url += `q=${encodeURIComponent(query)}&`
      } else if (category) {
        url += `category=${category}&`
      } else {
        url += 'category=general&'
      }
      
      url += `apiKey=${this.NEWS_API_KEY}&pageSize=5&sortBy=publishedAt`

      const response = await fetch(url)
      if (!response.ok) throw new Error(`News API error: ${response.status}`)
      
      const data = await response.json()
      return data.articles || []
    } catch (error) {
      console.error('Error fetching news:', error)
      return []
    }
  }

  // Sports news specifically
  static async getSportsNews(query?: string): Promise<NewsArticle[]> {
    try {
  if (!this.WEB_SEARCH_ENABLED) return []
  if (this.FREE_ONLY) return []
      if (!this.NEWS_API_KEY) return []

      let url = 'https://newsapi.org/v2/everything?'
      
      if (query) {
        url += `q=${encodeURIComponent(query)}&`
      } else {
        url += 'q=sports&'
      }
      
      url += `apiKey=${this.NEWS_API_KEY}&pageSize=5&sortBy=publishedAt&language=en`

      const response = await fetch(url)
      if (!response.ok) throw new Error(`Sports News API error: ${response.status}`)
      
      const data = await response.json()
      return data.articles || []
    } catch (error) {
      console.error('Error fetching sports news:', error)
      return []
    }
  }

  // CoinGecko API - Crypto prices with API key support
  static async getCryptoPrices(symbols: string[] = ['bitcoin', 'ethereum', 'cardano']): Promise<CryptoPrice[]> {
    try {
      const ids = symbols.join(',')
      let url = `https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=usd&include_market_cap=true&include_24hr_change=true&include_last_updated_at=true`
      
      const headers: Record<string, string> = {
        'Accept': 'application/json'
      }
      
      // Add API key if available for higher rate limits
      if (this.COINGECKO_API_KEY) {
        headers['x-cg-demo-api-key'] = this.COINGECKO_API_KEY
        console.log('Using CoinGecko API key for enhanced rate limits')
      }
      
      const response = await fetch(url, { headers })
      if (!response.ok) {
        throw new Error(`CoinGecko API error: ${response.status}`)
      }
      
      const data = await response.json()
      
      return Object.entries(data).map(([id, priceData]: [string, any]) => ({
        id,
        symbol: id,
        name: id.charAt(0).toUpperCase() + id.slice(1),
        current_price: priceData.usd,
        price_change_percentage_24h: priceData.usd_24h_change || 0,
        market_cap: priceData.usd_market_cap || 0,
        last_updated: new Date(priceData.last_updated_at * 1000).toISOString()
      }))
    } catch (error) {
      console.error('Error fetching crypto prices:', error)
      return []
    }
  }

  // CoinGecko API - Detailed crypto information
  static async getCryptoDetails(coinId: string): Promise<any> {
    try {
      const headers: Record<string, string> = {
        'Accept': 'application/json'
      }
      
      if (this.COINGECKO_API_KEY) {
        headers['x-cg-demo-api-key'] = this.COINGECKO_API_KEY
      }

      const url = `https://api.coingecko.com/api/v3/coins/${coinId}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false`
      
      const response = await fetch(url, { headers })
      if (!response.ok) {
        throw new Error(`CoinGecko Details API error: ${response.status}`)
      }
      
      const data = await response.json()
      
      return {
        id: data.id,
        name: data.name,
        symbol: data.symbol?.toUpperCase(),
        current_price: data.market_data?.current_price?.usd,
        market_cap: data.market_data?.market_cap?.usd,
        market_cap_rank: data.market_cap_rank,
        price_change_24h: data.market_data?.price_change_percentage_24h,
        price_change_7d: data.market_data?.price_change_percentage_7d,
        price_change_30d: data.market_data?.price_change_percentage_30d,
        volume_24h: data.market_data?.total_volume?.usd,
        circulating_supply: data.market_data?.circulating_supply,
        total_supply: data.market_data?.total_supply,
        ath: data.market_data?.ath?.usd,
        ath_date: data.market_data?.ath_date?.usd,
        atl: data.market_data?.atl?.usd,
        atl_date: data.market_data?.atl_date?.usd,
        last_updated: data.last_updated
      }
    } catch (error) {
      console.error('Error fetching crypto details:', error)
      return null
    }
  }

  // Alpha Vantage API - Stock prices
  static async getStockPrice(symbol: string): Promise<StockPrice | null> {
    try {
      if (!this.ALPHA_VANTAGE_KEY) {
        console.log('Alpha Vantage API key not configured')
        return null
      }

      const url = `https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=${symbol}&apikey=${this.ALPHA_VANTAGE_KEY}`
      
      const response = await fetch(url)
      if (!response.ok) throw new Error(`Alpha Vantage API error: ${response.status}`)
      
      const data = await response.json()
      const quote = data['Global Quote']
      
      if (!quote) return null

      return {
        symbol: quote['01. symbol'],
        price: parseFloat(quote['05. price']),
        change: parseFloat(quote['09. change']),
        changePercent: parseFloat(quote['10. change percent'].replace('%', '')),
        volume: parseInt(quote['06. volume'])
      }
    } catch (error) {
      console.error('Error fetching stock price:', error)
      return null
    }
  }

  // Alternative free stock API
  static async getStockPriceFree(symbol: string): Promise<StockPrice | null> {
    try {
      // Using Yahoo Finance alternative API
      const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}`
      
      const response = await fetch(url)
      if (!response.ok) throw new Error(`Yahoo Finance API error: ${response.status}`)
      
      const data = await response.json()
      const result = data.chart?.result?.[0]
      
      if (!result) return null

      const meta = result.meta
      const currentPrice = meta.regularMarketPrice
      const previousClose = meta.previousClose
      const change = currentPrice - previousClose
      const changePercent = (change / previousClose) * 100

      return {
        symbol: meta.symbol,
        price: currentPrice,
        change: change,
        changePercent: changePercent,
        marketCap: meta.marketCap,
        volume: meta.regularMarketVolume
      }
    } catch (error) {
      console.error('Error fetching stock price (free):', error)
      return null
    }
  }

  // Weather API
  static async getWeather(city: string): Promise<WeatherData | null> {
    try {
      if (!this.WEATHER_API_KEY) {
        console.log('Weather API key not configured')
        return null
      }

      const url = `https://api.openweathermap.org/data/2.5/weather?q=${encodeURIComponent(city)}&appid=${this.WEATHER_API_KEY}&units=metric`
      
      const response = await fetch(url)
      if (!response.ok) throw new Error(`Weather API error: ${response.status}`)
      
      const data = await response.json()

      return {
        location: `${data.name}, ${data.sys.country}`,
        temperature: data.main.temp,
        condition: data.weather[0].description,
        humidity: data.main.humidity,
        windSpeed: data.wind.speed
      }
    } catch (error) {
      console.error('Error fetching weather:', error)
      return null
    }
  }

  // FastForex API - Premium exchange rates
  static async getExchangeRatesFast(baseCurrency: string = 'USD'): Promise<any> {
    try {
      if (!this.FASTFOREX_API_KEY) {
        console.log('FastForex API key not configured, using fallback')
        return await this.getExchangeRates(baseCurrency)
      }

      const url = `https://api.fastforex.io/fetch-all?from=${baseCurrency}&api_key=${this.FASTFOREX_API_KEY}`
      
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`FastForex API error: ${response.status}`)
      }
      
      const data = await response.json()
      
      return {
        base: data.base,
        rates: data.results,
        updated: data.updated
      }
    } catch (error) {
      console.error('Error fetching exchange rates from FastForex:', error)
      // Fallback to free API
      return await this.getExchangeRates(baseCurrency)
    }
  }

  // Exchange rates - Free API fallback
  static async getExchangeRates(baseCurrency: string = 'USD'): Promise<any> {
    try {
      const url = `https://api.exchangerate-api.com/v4/latest/${baseCurrency}`
      
      const response = await fetch(url)
      if (!response.ok) throw new Error(`Exchange rate API error: ${response.status}`)
      
      const data = await response.json()
      return {
        base: data.base,
        rates: data.rates,
        updated: data.date
      }
    } catch (error) {
      console.error('Error fetching exchange rates:', error)
      return null
    }
  }

  // Fact-check search across reputable domains using SERPER
  static async getFactChecks(query: string): Promise<Array<{ title: string; url: string; publisher?: string; publishedAt?: string; rating?: string; snippet?: string }>> {
  if (!this.WEB_SEARCH_ENABLED) return []
  const SERPER_API_KEY = process.env.SERPER_API_KEY
  // Prefer Google Fact Check API when key is configured (still free)
  if (this.GOOGLE_FACTCHECK_API_KEY) {
      const viaGfc = await this.googleFactCheck(query, 10)
      if (viaGfc.length) return viaGfc
    }
  if (!SERPER_API_KEY || this.FREE_ONLY) {
      // Fallback to Google News RSS search constrained to fact-check domains
      const factDomains = [
        'snopes.com', 'politifact.com', 'factcheck.org', 'reuters.com', 'apnews.com', 'fullfact.org', 'leadstories.com', 'turnbackhoax.id', 'kominfo.go.id'
      ]
      const rssQuery = `${query} (${factDomains.map(d => `site:${d}`).join(' OR ')})`
      const rss = await this.googleNewsRSS(rssQuery, { max: 10 })
      return rss.map(a => ({ title: a.title, url: a.url, publisher: a.source.name, publishedAt: a.publishedAt }))
    }
    const factDomains = [
      'snopes.com',
      'politifact.com',
      'factcheck.org',
      'reuters.com',
      'apnews.com',
      'fullfact.org',
      'leadstories.com',
      'turnbackhoax.id',
      'kominfo.go.id'
    ]
    const queryStr = `${query} (site:${factDomains.join(' OR site:')})`
    try {
      const response = await fetch('https://google.serper.dev/search', {
        method: 'POST',
        headers: {
          'X-API-KEY': SERPER_API_KEY,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ q: queryStr, num: 10 })
      })
      if (!response.ok) throw new Error(`SERPER fact-check error: ${response.status}`)
      const data = await response.json()
      const items: Array<{ title: string; url: string; publisher?: string; publishedAt?: string; rating?: string; snippet?: string }> = []
      const take = (arr: any[]) => {
        arr.forEach((item: any) => {
          // Prefer exact article link from the result
          const link = item.link || item.url
          if (!link) return
          const host = (() => { try { return new URL(link).hostname } catch { return '' } })()
          if (!factDomains.some(d => host.includes(d))) return
          const title = item.title || item.titleRaw || link
          const snippet = item.snippet || item.description || ''
          const source = item.source || item.publisher || (host.replace('www.', ''))
          const date = item.date || item.publishedDate || undefined
          const rating = ExternalDataService.extractFactRating(title, snippet)
          items.push({ title, url: link, publisher: source, publishedAt: date, rating, snippet })
        })
      }
      if (Array.isArray(data.news)) take(data.news)
      if (Array.isArray(data.organic)) take(data.organic)
      // De-dup by URL
      const seen = new Set<string>()
      const unique = items.filter(i => { if (seen.has(i.url)) return false; seen.add(i.url); return true })
      return unique.slice(0, 8)
    } catch (err) {
      console.error('Error fetching fact-checks:', err)
      return []
    }
  }

  private static extractFactRating(title: string, snippet?: string): string | undefined {
    const text = `${title} ${snippet || ''}`.toLowerCase()
    const ratings = [
      { k: 'false', v: 'False' },
      { k: 'true', v: 'True' },
      { k: 'mostly false', v: 'Mostly False' },
      { k: 'mostly true', v: 'Mostly True' },
      { k: 'partly false', v: 'Partly False' },
      { k: 'mixture', v: 'Mixture' },
      { k: 'unproven', v: 'Unproven' },
      { k: 'misleading', v: 'Misleading' },
      { k: 'no evidence', v: 'No Evidence' },
    ]
    for (const r of ratings) {
      if (text.includes(r.k)) return r.v
    }
    return undefined
  }

  // Formula 1 API (Enhanced with better validation)
  static async getF1Results(): Promise<any> {
    try {
      // Using Ergast F1 API
      const currentYear = new Date().getFullYear()
      const url = `https://ergast.com/api/f1/${currentYear}/last/results.json`
      
      console.log(`Fetching F1 data from: ${url}`)
      const response = await fetch(url)
      if (!response.ok) throw new Error(`F1 API error: ${response.status}`)
      
      const data = await response.json()
      const race = data.MRData?.RaceTable?.Races?.[0]
      
      if (!race) {
        console.log('No F1 race data found')
        return null
      }

      const result = {
        raceName: race.raceName,
        date: race.date,
        round: race.round,
        season: race.season,
        winner: race.Results?.[0]?.Driver?.familyName,
        winnerFullName: `${race.Results?.[0]?.Driver?.givenName} ${race.Results?.[0]?.Driver?.familyName}`,
        constructor: race.Results?.[0]?.Constructor?.name,
        circuit: race.Circuit?.circuitName,
        country: race.Circuit?.Location?.country,
        url: race.url,
        // Add validation timestamp
        fetchedAt: new Date().toISOString(),
        // Add top 3 for better validation
        podium: race.Results?.slice(0, 3)?.map((result: any) => ({
          position: result.position,
          driver: `${result.Driver?.givenName} ${result.Driver?.familyName}`,
          constructor: result.Constructor?.name
        }))
      }
      
      console.log('F1 data successfully fetched:', result)
      return result
    } catch (error) {
      console.error('Error fetching F1 results:', error)
      return null
    }
  }

  // Enhanced data enrichment function
  static async enrichQueryWithExternalData(query: string): Promise<string> {
    const queryLower = query.toLowerCase()
    let enrichedContext = ''
      // Fact-check / hoax queries (multi-language)
      if (
        queryLower.includes('hoax') || queryLower.includes('hoaks') ||
        queryLower.includes('fact check') || queryLower.includes('fact-check') ||
        queryLower.includes('apakah benar') || queryLower.includes('benarkah') ||
        queryLower.includes('is it true') || queryLower.includes('fake news') ||
        queryLower.includes('disinformation') || queryLower.includes('misinformation')
      ) {
        console.log('Fact-check query detected, searching reputable sources...')
        const facts = await this.getFactChecks(query)
        if (facts.length > 0) {
          enrichedContext += `\n\nVERIFIED FACT-CHECK FINDINGS:\n` +
            facts.slice(0, 5).map((f, i) => `${i + 1}. ${f.title}${f.rating ? ` [${f.rating}]` : ''} - ${f.publisher || ''} (${f.publishedAt ? new Date(f.publishedAt).toLocaleDateString() : ''})\n${f.url}`).join('\n')
        } else {
          enrichedContext += `\n\nFACT-CHECK SOURCES NOT FOUND or unavailable at this time.`
        }
      }

    try {
      // Formula 1 / Sports queries
      if (queryLower.includes('formula 1') || queryLower.includes('f1') || 
          (queryLower.includes('race') && queryLower.includes('won'))) {
        console.log('F1 query detected, fetching external F1 data...')
        const f1Data = await this.getF1Results()
        if (f1Data) {
          enrichedContext += `\n\nVERIFIED F1 DATA (Ergast API - Official Source):
Race: ${f1Data.raceName} 
Date: ${f1Data.date}
Season: ${f1Data.season}, Round: ${f1Data.round}
Winner: ${f1Data.winnerFullName} (${f1Data.constructor})
Circuit: ${f1Data.circuit}, ${f1Data.country}
Data Source: Official Ergast F1 API
Fetched: ${f1Data.fetchedAt}

PODIUM RESULTS:
${f1Data.podium?.map((p: any) => `${p.position}. ${p.driver} (${p.constructor})`).join('\n') || 'Podium data unavailable'}

IMPORTANT: Use ONLY this verified data for F1 race results. Do not speculate or use outdated information.`
        } else {
          enrichedContext += `\n\nF1 DATA UNAVAILABLE: External F1 API (Ergast) is not accessible. Cannot verify current race results.`
        }

        // Get F1 related news
        const f1News = await this.getSportsNews('Formula 1 OR F1')
        if (f1News.length > 0) {
          enrichedContext += `\n\nLATEST F1 NEWS:\n`
          f1News.slice(0, 3).forEach((article, i) => {
            enrichedContext += `${i + 1}. ${article.title} (${new Date(article.publishedAt).toLocaleDateString()})\n`
          })
        }
      }

      // Crypto queries - Enhanced with detailed data
      if (queryLower.includes('bitcoin') || queryLower.includes('crypto') || 
          queryLower.includes('ethereum') || queryLower.includes('btc') || 
          queryLower.includes('cardano') || queryLower.includes('ada')) {
        
        // Get basic prices first
        const cryptoPrices = await this.getCryptoPrices(['bitcoin', 'ethereum', 'cardano'])
        if (cryptoPrices.length > 0) {
          enrichedContext += `\n\nREAL-TIME CRYPTO PRICES (CoinGecko):\n`
          cryptoPrices.forEach(crypto => {
            const changeSign = crypto.price_change_percentage_24h >= 0 ? '+' : ''
            enrichedContext += `${crypto.name}: $${crypto.current_price.toLocaleString()} (${changeSign}${crypto.price_change_percentage_24h.toFixed(2)}% 24h)\n`
          })
        }

        // Get detailed data for specific coin if mentioned
        let specificCoin = null
        if (queryLower.includes('bitcoin') || queryLower.includes('btc')) specificCoin = 'bitcoin'
        else if (queryLower.includes('ethereum') || queryLower.includes('eth')) specificCoin = 'ethereum'
        else if (queryLower.includes('cardano') || queryLower.includes('ada')) specificCoin = 'cardano'

        if (specificCoin) {
          const details = await this.getCryptoDetails(specificCoin)
          if (details) {
            enrichedContext += `\n${details.name} (${details.symbol}) Details:
Market Cap: $${details.market_cap?.toLocaleString() || 'N/A'} (Rank #${details.market_cap_rank || 'N/A'})
24h Volume: $${details.volume_24h?.toLocaleString() || 'N/A'}
All-Time High: $${details.ath?.toLocaleString() || 'N/A'}
7d Change: ${details.price_change_7d ? (details.price_change_7d >= 0 ? '+' : '') + details.price_change_7d.toFixed(2) + '%' : 'N/A'}\n`
          }
        }
      }

      // Stock queries
      const stockSymbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
      const stockMentioned = stockSymbols.some(symbol => 
        queryLower.includes(symbol.toLowerCase()) || 
        queryLower.includes('stock') || 
        queryLower.includes('shares')
      )
      
      if (stockMentioned) {
        // Try to extract specific stock symbol from query
        let targetSymbol = 'AAPL' // default
        for (const symbol of stockSymbols) {
          if (queryLower.includes(symbol.toLowerCase())) {
            targetSymbol = symbol
            break
          }
        }

        const stockData = await this.getStockPriceFree(targetSymbol)
        if (stockData) {
          const changeSign = stockData.change >= 0 ? '+' : ''
          enrichedContext += `\n\nREAL-TIME STOCK DATA:
${stockData.symbol}: $${stockData.price.toFixed(2)} (${changeSign}${stockData.change.toFixed(2)}, ${changeSign}${stockData.changePercent.toFixed(2)}%)`
        }
      }

      // News queries
      if (queryLower.includes('news') || queryLower.includes('latest') || 
          queryLower.includes('recent') || queryLower.includes('today')) {
        const news = await this.getLatestNews()
        if (news.length > 0) {
          enrichedContext += `\n\nLATEST NEWS HEADLINES:\n`
          news.slice(0, 3).forEach((article, i) => {
            enrichedContext += `${i + 1}. ${article.title} (${article.source.name}, ${new Date(article.publishedAt).toLocaleDateString()})\n`
          })
        }
      }

      // Exchange rate queries
      if (queryLower.includes('exchange') || queryLower.includes('currency') || 
          queryLower.includes('usd') || queryLower.includes('eur') || 
          queryLower.includes('rate') || queryLower.includes('convert')) {
        
        // Try to extract currencies from query
        const currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY']
        const mentionedCurrencies = currencies.filter(curr => 
          queryLower.includes(curr.toLowerCase())
        )

        let baseCurrency = 'USD'
        if (mentionedCurrencies.length > 0) {
          baseCurrency = mentionedCurrencies[0]
        }

        // Use FastForex API if available, fallback to free API
        const exchangeData = await this.getExchangeRatesFast(baseCurrency)
        if (exchangeData && exchangeData.rates) {
          enrichedContext += `\n\nREAL-TIME EXCHANGE RATES (Base: ${exchangeData.base}):\n`
          
          // Show major currencies
          const majorCurrencies = ['EUR', 'GBP', 'JPY', 'CAD', 'AUD']
          majorCurrencies.forEach(currency => {
            if (exchangeData.rates[currency] && currency !== baseCurrency) {
              enrichedContext += `${baseCurrency}/${currency}: ${exchangeData.rates[currency].toFixed(4)}\n`
            }
          })
          
          if (exchangeData.updated) {
            enrichedContext += `Updated: ${exchangeData.updated}\n`
          }
        }
      }

      // Weather queries
      if (queryLower.includes('weather') || queryLower.includes('temperature')) {
        // Try to extract city name (basic extraction)
        const cities = ['london', 'new york', 'tokyo', 'paris', 'sydney', 'singapore']
        const mentionedCity = cities.find(city => queryLower.includes(city))
        
        if (mentionedCity) {
          const weather = await this.getWeather(mentionedCity)
          if (weather) {
            enrichedContext += `\n\nCURRENT WEATHER:
${weather.location}: ${weather.temperature}°C, ${weather.condition}
Humidity: ${weather.humidity}%, Wind: ${weather.windSpeed} m/s`
          }
        }
      }

    } catch (error) {
      console.error('Error enriching query with external data:', error)
    }

    return enrichedContext
  }

  // SERPER API - Google Search untuk artikel berita
  static async searchRelevantArticles(query: string): Promise<NewsArticle[]> {
  if (!ExternalDataService.WEB_SEARCH_ENABLED) return []
    const SERPER_API_KEY = process.env.SERPER_API_KEY
    if (!SERPER_API_KEY || this.FREE_ONLY) {
      // Use Google News RSS when running in free-only mode or without SERPER
      return await this.googleNewsRSS(query, { max: 10 })
    }

    try {
      // Search for news articles using SERPER
      const response = await fetch('https://google.serper.dev/search', {
        method: 'POST',
        headers: {
          'X-API-KEY': SERPER_API_KEY,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          q: query,
          num: 10,
          gl: 'us',
          hl: 'en'
        })
      })

      if (!response.ok) {
        throw new Error(`SERPER API error: ${response.status}`)
      }

      const data = await response.json()
      const articles: NewsArticle[] = []

      if (data.news) {
        for (const item of data.news as any[]) {
          const raw = item.link || item.url
          if (!raw) continue
          const cleaned = this.normalizeUrl(raw)
          const resolved = await this.resolveUrlWithHead(cleaned)
          if (this.isAggregatorOrHomepage(resolved)) continue
          const meta = await this.fetchMetaQuick(resolved)
          const finalDesc = (meta?.description || item.snippet || item.title)
          if (!this.looksLikeArticle(resolved)) continue
          if (this.isGenericSnippet(finalDesc, item.title)) continue
          if (!this.isRelevant(item.title, finalDesc, query)) continue
          articles.push({
            title: item.title,
            description: finalDesc,
            url: resolved,
            publishedAt: (meta?.publishedAt || item.date || new Date().toISOString()),
            source: { name: (meta?.publisher || item.source || 'Unknown Source') }
          })
        }
      }

      // Prefer deep article links and filter shallow homepages when deeper links exist
  const hasDeep = articles.some(a => this.deepScore(a.url) >= 2)
      const filtered = hasDeep
        ? articles.filter(a => this.deepScore(a.url) >= 2 || !this.isUtilityHomepage(a.url))
        : articles

      // De-dup and sort by deepness then recency
  const unique = filtered.filter((a, i, self) => i === self.findIndex(b => b.url === a.url))
      return unique.sort((a, b) => {
        const ds = this.deepScore(b.url) - this.deepScore(a.url)
        if (ds !== 0) return ds
        return new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()
      })
    } catch (error) {
      console.error('Error searching with SERPER:', error)
      return []
    }
  }

  // Combined function: Get relevant articles from multiple sources
  static async getRelevantArticles(query: string): Promise<NewsArticle[]> {
  if (!this.WEB_SEARCH_ENABLED) return []
  const allArticles: NewsArticle[] = []

    try {
  // Assemble from multiple sources with priority and fallback
  // 0) If this looks like a claim/hoax check, prioritize Google Fact Check
  const isClaim = this.isClaimQuery(query)
  if (isClaim) {
    // For claim/hoax: ONLY use fact-check/space authority sources, no Guardian/RSS fallback at all
    const facts = await this.googleFactCheck(query, 10)
    for (const f of facts) {
      const mapped: NewsArticle = {
        title: f.title,
        description: [f.rating, f.snippet].filter(Boolean).join(' — '),
        url: this.normalizeUrl(f.url),
        publishedAt: f.publishedAt || new Date().toISOString(),
        source: { name: f.publisher || 'Fact Check' }
      }
      allArticles.push(mapped)
    }
    // After allowlist filtering, if no valid sources, forcibly set allArticles to []
    if (allArticles.length === 0) {
      return []
    }
  } else {
    // 1) Guardian (free key, stricter relevance)
    const guardian = await this.guardianSearch(query, 10)
    allArticles.push(...guardian)
    // 2) SERPER/Google News RSS as discovery fallback
    const serperOrRss = await this.searchRelevantArticles(query)
    allArticles.push(...serperOrRss)
  }

      // 3. Normalize, resolve, enrich missing meta, and validate relevance/quality
      const normed: NewsArticle[] = []
      for (const a of allArticles) {
        try {
          const cleaned = this.normalizeUrl(a.url)
          const resolved = await this.resolveUrlWithHead(cleaned)
          if (this.isAggregatorOrHomepage(resolved)) continue
          if (!this.looksLikeArticle(resolved)) continue
          let desc = a.description
          if (this.isGenericSnippet(desc, a.title)) {
            const meta = await this.fetchMetaQuick(resolved)
            if (meta?.description && !this.isGenericSnippet(meta.description, a.title)) {
              desc = meta.description
              // Prefer publisher/date from meta when present
              a.source = { name: meta.publisher || a.source?.name || 'Unknown Source' }
              a.publishedAt = meta.publishedAt || a.publishedAt
            } else {
              continue
            }
          }
          if (!this.isRelevant(a.title, desc, query)) continue
          // For claim-style queries, keep only reputable fact-check domains and relevant authorities (NASA/ESA/WHO/CDC, etc.)
          if (isClaim) {
            try {
              const host = new URL(resolved).hostname.replace(/^www\./, '')
              // Add ESA, JPL, and other space authorities for 'visible from space' claims
              const spaceHosts = /(nasa\.gov|esa\.int|jpl\.nasa\.gov|space\.com|universetoday\.com|earthobservatory\.nasa\.gov|noaa\.gov|usgs\.gov)/i
              const factHosts = /(snopes\.com|politifact\.com|factcheck\.org|fullfact\.org|reuters\.com|apnews\.com|leadstories\.com|turnbackhoax\.id|kominfo\.go\.id|who\.int|cdc\.gov|nih\.gov|fda\.gov|ema\.europa\.eu|nhs\.uk|unicef\.org)/i
              // If the query is about 'visible from space', require space authority or fact-check
              if (/visible from space|see from space|seen from space|astronaut/i.test(query)) {
                if (!(spaceHosts.test(host) || factHosts.test(host))) continue
              } else {
                if (!(factHosts.test(host))) continue
              }
            } catch {}
          }
          normed.push({ ...a, url: resolved, description: desc })
        } catch {}
      }

      // 4. Prefer deep links and filter shallow when deeper exists
      const hasDeep = normed.some(a => ExternalDataService.deepScore(a.url) >= 2)
      const filtered = hasDeep
        ? normed.filter(a => ExternalDataService.deepScore(a.url) >= 2 || !ExternalDataService.isUtilityHomepage(a.url))
        : normed

      // 5. Remove duplicates and sort by deepness then date
      const uniqueArticles = filtered.filter((article, index, self) => 
        index === self.findIndex(a => a.url === article.url)
      )
      // For claim/hoax queries, if no valid sources remain after filtering, return [] (hide sources)
      if (isClaim && uniqueArticles.length === 0) return []
      return uniqueArticles
        .sort((a, b) => {
          const ds = ExternalDataService.deepScore(b.url) - ExternalDataService.deepScore(a.url)
          if (ds !== 0) return ds
          return new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()
        })
        .slice(0, 8)

    } catch (error) {
      console.error('Error getting relevant articles:', error)
      return allArticles.slice(0, 3) // Return at least some articles
    }
  }
}

// Export standalone function for easier import
export async function getRelevantArticles(query: string): Promise<NewsArticle[]> {
  return ExternalDataService.getRelevantArticles(query)
}
