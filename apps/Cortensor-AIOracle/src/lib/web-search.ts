// Web search service untuk mendapatkan informasi terkini
class WebSearchService {
  private static async searchDuckDuckGo(query: string): Promise<string[]> {
    try {
      const searchUrl = `https://api.duckduckgo.com/?q=${encodeURIComponent(query)}&format=json&no_html=1&skip_disambig=1`
      const response = await fetch(searchUrl)
      const data = await response.json()
      
      const results: string[] = []
      if (data.AbstractText) {
        results.push(data.AbstractText)
      }
      
      return results
    } catch (error) {
      console.error('DuckDuckGo search failed:', error)
      return []
    }
  }

  private static async searchSerper(query: string): Promise<string[]> {
    const SERPER_API_KEY = process.env.SERPER_API_KEY
    if (!SERPER_API_KEY) return []
    
    try {
      const response = await fetch('https://google.serper.dev/search', {
        method: 'POST',
        headers: {
          'X-API-KEY': SERPER_API_KEY,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          q: query,
          num: 5
        })
      })
      
      const data = await response.json()
      const results: string[] = []
      
      if (data.organic) {
        data.organic.slice(0, 3).forEach((item: any) => {
          if (item.snippet) {
            results.push(`${item.title}: ${item.snippet}`)
          }
        })
      }
      
      return results
    } catch (error) {
      console.error('Serper search failed:', error)
      return []
    }
  }

  static async getRealtimeInfo(query: string): Promise<string> {
    // Try multiple search sources
    const searchPromises = [
      this.searchDuckDuckGo(query),
      this.searchSerper(query)
    ]
    
    const results = await Promise.allSettled(searchPromises)
    const allResults: string[] = []
    
    results.forEach(result => {
      if (result.status === 'fulfilled') {
        allResults.push(...result.value)
      }
    })
    
    if (allResults.length === 0) {
      return "No current information found from web search."
    }
    
    return `Current information from web search:\n${allResults.join('\n\n')}`
  }
}

export { WebSearchService }
