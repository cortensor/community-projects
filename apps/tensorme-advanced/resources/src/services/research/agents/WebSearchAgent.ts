import { ResearchAgent } from './BaseAgent';
import { AgentTask, AgentResult, Finding, Source } from '@/types/research';
import { generateId } from '@/lib/utils';

interface SearchResult {
  title: string;
  snippet: string;
  url: string;
  date?: string;
  source?: string;
}

export class WebSearchAgent extends ResearchAgent {
  constructor() {
    super('web_search');
  }

  /**
   * Execute web search task
   */
  public async execute(task: AgentTask): Promise<AgentResult> {
    try {
      await this.reportProgress(20, 'Generating search queries...');
      
      // Generate multiple search queries from the task
      const searchQueries = this.generateSearchQueries(task.query, task.context);
      
      await this.reportProgress(30, `Searching ${searchQueries.length} queries...`);
      
      // Execute searches in parallel
      const allResults: SearchResult[] = [];
      for (let i = 0; i < searchQueries.length; i++) {
        const query = searchQueries[i];
        await this.reportProgress(30 + (i * 15), `Searching: ${query}`);
        
        const results = await this.performSearch(query, task.constraints?.domains);
        allResults.push(...results);
      }
      
      await this.reportProgress(75, 'Analyzing search results...');
      
      // Process and rank results
      const findings = await this.processSearchResults(
        allResults, 
        task.query,
        task.constraints?.maxResults || 5
      );
      
      // Report findings as they're created
      for (const finding of findings) {
        await this.reportFinding(finding);
      }
      
      await this.reportProgress(90, 'Validating sources...');
      
      return {
        agentId: this.id,
        taskId: task.id,
        success: true,
        findings,
        metadata: {
          sourcesChecked: allResults.length,
          confidence: this.calculateOverallConfidence(findings),
          processingTime: Date.now()
        }
      };
    } catch (error) {
      return {
        agentId: this.id,
        taskId: task.id,
        success: false,
        findings: [],
        errors: [error instanceof Error ? error.message : 'Search failed']
      };
    }
  }

  /**
   * Generate multiple search queries from the task
   */
  private generateSearchQueries(query: string, context?: string): string[] {
    const queries: string[] = [];
    
    // Original query
    queries.push(query);
    
    // Add context if provided
    if (context) {
      queries.push(`${context} ${query}`);
    }
    
    // Add variations
    if (query.includes('vs') || query.includes('versus')) {
      // Comparison query - search each item separately
      const parts = query.split(/\bvs\b|\bversus\b/i);
      parts.forEach(part => queries.push(part.trim()));
    }
    
    // Add question variations
    if (!query.includes('?')) {
      queries.push(`what is ${query}`);
      queries.push(`how does ${query} work`);
    }
    
    // Add recent/latest variant
    queries.push(`${query} ${new Date().getFullYear()}`);
    queries.push(`latest ${query}`);
    
    // Limit to unique queries
    return [...new Set(queries)].slice(0, 5);
  }

  /**
   * Perform actual web search
   * In production, this would use a real search API (Google, Bing, etc.)
   */
  private async performSearch(
    query: string, 
    domains?: string[]
  ): Promise<SearchResult[]> {
    // For now, we'll simulate search results
    // In production, integrate with search APIs like:
    // - Google Custom Search API
    // - Bing Search API
    // - SerpAPI
    // - Brave Search API
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Generate mock results based on query
    const mockResults: SearchResult[] = [];
    
    // Simulate different types of sources
    const sourceTypes = [
      { domain: 'wikipedia.org', credibility: 0.8, type: 'encyclopedia' },
      { domain: 'arxiv.org', credibility: 0.9, type: 'academic' },
      { domain: 'medium.com', credibility: 0.6, type: 'blog' },
      { domain: 'news.ycombinator.com', credibility: 0.7, type: 'forum' },
      { domain: 'github.com', credibility: 0.8, type: 'code' }
    ];
    
    // Filter by domains if specified
    const availableSources = domains?.length 
      ? sourceTypes.filter(s => domains.some(d => s.domain.includes(d)))
      : sourceTypes;
    
    // Generate 3-5 results per query
    const resultCount = Math.floor(Math.random() * 3) + 3;
    
    for (let i = 0; i < Math.min(resultCount, availableSources.length); i++) {
      const source = availableSources[i];
      mockResults.push({
        title: `${query} - ${source.type} result`,
        snippet: `This is a detailed explanation about ${query}. The content discusses various aspects including implementation, benefits, and considerations. Recent developments show significant progress in this area.`,
        url: `https://${source.domain}/article-${generateId()}`,
        date: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
        source: source.domain
      });
    }
    
    return mockResults;
  }

  /**
   * Process search results into findings
   */
  private async processSearchResults(
    results: SearchResult[],
    originalQuery: string,
    maxFindings: number
  ): Promise<Finding[]> {
    const findings: Finding[] = [];
    
    // Deduplicate results by URL
    const uniqueResults = this.deduplicateResults(results);
    
    // Rank results by relevance
    const rankedResults = this.rankResults(uniqueResults, originalQuery);
    
    // Convert top results to findings
    for (const result of rankedResults.slice(0, maxFindings)) {
      const finding = await this.createFindingFromResult(result, originalQuery);
      findings.push(finding);
    }
    
    return findings;
  }

  /**
   * Deduplicate search results
   */
  private deduplicateResults(results: SearchResult[]): SearchResult[] {
    const seen = new Set<string>();
    return results.filter(result => {
      const key = result.url || result.title;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  /**
   * Rank results by relevance
   */
  private rankResults(results: SearchResult[], query: string): SearchResult[] {
    return results.sort((a, b) => {
      const scoreA = this.calculateResultScore(a, query);
      const scoreB = this.calculateResultScore(b, query);
      return scoreB - scoreA;
    });
  }

  /**
   * Calculate relevance score for a search result
   */
  private calculateResultScore(result: SearchResult, query: string): number {
    let score = 0;
    
    const queryLower = query.toLowerCase();
    const titleLower = result.title.toLowerCase();
    const snippetLower = result.snippet.toLowerCase();
    
    // Title matches
    if (titleLower.includes(queryLower)) score += 3;
    
    // Snippet matches
    const queryWords = queryLower.split(' ');
    queryWords.forEach(word => {
      if (snippetLower.includes(word)) score += 1;
    });
    
    // Recency bonus
    if (result.date) {
      const age = Date.now() - new Date(result.date).getTime();
      const daysOld = age / (1000 * 60 * 60 * 24);
      if (daysOld < 7) score += 2;
      else if (daysOld < 30) score += 1;
    }
    
    // Source credibility bonus
    if (result.source) {
      if (result.source.includes('.edu') || result.source.includes('.gov')) score += 2;
      if (result.source.includes('wikipedia') || result.source.includes('arxiv')) score += 1;
    }
    
    return score;
  }

  /**
   * Create a finding from a search result
   */
  private async createFindingFromResult(
    result: SearchResult,
    query: string
  ): Promise<Finding> {
    // Extract key information from snippet
    const content = await this.extractKeyInformation(result.snippet, query);
    
    // Determine credibility
    const credibility = this.assessSourceCredibility(result);
    
    // Create source
    const source: Source = {
      title: result.title,
      url: result.url,
      date: result.date ? new Date(result.date) : undefined,
      credibility,
      type: this.determineSourceType(result.source || result.url)
    };
    
    // Calculate confidence based on multiple factors
    const confidence = this.calculateConfidence(result, query, credibility);
    
    // Determine category
    const category = this.determineCategory(content);
    
    return {
      id: generateId(),
      agentId: this.id,
      content,
      confidence,
      sources: [source],
      timestamp: new Date(),
      category,
      relevance: this.calculateRelevance(content, query),
      tags: this.extractTags(content)
    };
  }

  /**
   * Extract key information from snippet
   */
  private async extractKeyInformation(snippet: string, query: string): Promise<string> {
    // In production, this could use an LLM to extract and summarize
    // For now, we'll do simple extraction
    
    // Find sentences containing query terms
    const sentences = snippet.split(/[.!?]+/);
    const queryWords = query.toLowerCase().split(' ');
    
    const relevantSentences = sentences.filter(sentence => {
      const sentenceLower = sentence.toLowerCase();
      return queryWords.some(word => sentenceLower.includes(word));
    });
    
    if (relevantSentences.length > 0) {
      return relevantSentences.join('. ').trim() + '.';
    }
    
    // Fallback to first sentence
    return sentences[0]?.trim() + '.' || snippet;
  }

  /**
   * Assess source credibility
   */
  private assessSourceCredibility(result: SearchResult): number {
    let credibility = 0.5; // Base credibility
    
    const source = result.source || result.url;
    
    // Academic sources
    if (source.includes('.edu') || source.includes('arxiv') || source.includes('scholar')) {
      credibility = 0.9;
    }
    // Government sources
    else if (source.includes('.gov')) {
      credibility = 0.9;
    }
    // Major news outlets
    else if (source.match(/bbc|cnn|reuters|nytimes|washingtonpost|guardian/i)) {
      credibility = 0.8;
    }
    // Wikipedia
    else if (source.includes('wikipedia')) {
      credibility = 0.75;
    }
    // Technical sources
    else if (source.includes('github') || source.includes('stackoverflow')) {
      credibility = 0.7;
    }
    // Blogs and forums
    else if (source.includes('medium') || source.includes('reddit')) {
      credibility = 0.6;
    }
    
    return credibility;
  }

  /**
   * Determine source type
   */
  private determineSourceType(source: string): Source['type'] {
    if (source.includes('.edu') || source.includes('arxiv') || source.includes('scholar')) {
      return 'academic';
    }
    if (source.includes('.gov') || source.match(/bbc|cnn|reuters|nytimes/i)) {
      return 'news';
    }
    if (source.includes('blog') || source.includes('medium')) {
      return 'blog';
    }
    if (source.includes('twitter') || source.includes('reddit') || source.includes('facebook')) {
      return 'social';
    }
    if (source.includes('.gov') || source.includes('.org')) {
      return 'official';
    }
    return 'unknown';
  }

  /**
   * Calculate confidence for a finding
   */
  private calculateConfidence(
    result: SearchResult,
    query: string,
    credibility: number
  ): number {
    // Start with source credibility
    let confidence = credibility;
    
    // Adjust based on relevance
    const relevance = this.calculateResultScore(result, query) / 10; // Normalize to 0-1
    confidence = (confidence + relevance) / 2;
    
    // Adjust based on recency
    if (result.date) {
      const age = Date.now() - new Date(result.date).getTime();
      const monthsOld = age / (1000 * 60 * 60 * 24 * 30);
      if (monthsOld > 12) {
        confidence *= 0.9; // Reduce confidence for older sources
      }
    }
    
    return Math.min(Math.max(confidence, 0), 1); // Clamp between 0 and 1
  }

  /**
   * Determine category of finding
   */
  private determineCategory(content: string): Finding['category'] {
    const contentLower = content.toLowerCase();
    
    if (contentLower.match(/\d+%|\d+ percent|statistics|survey|study shows/)) {
      return 'statistic';
    }
    if (contentLower.includes('"') || contentLower.includes('said') || contentLower.includes('stated')) {
      return 'quote';
    }
    if (contentLower.includes('believe') || contentLower.includes('think') || contentLower.includes('opinion')) {
      return 'opinion';
    }
    if (contentLower.includes('fact') || contentLower.includes('proven') || contentLower.includes('confirmed')) {
      return 'fact';
    }
    
    return 'analysis';
  }

  /**
   * Extract tags from content
   */
  private extractTags(content: string): string[] {
    const tags: string[] = [];
    
    // Extract technical terms (capitalized words)
    const matches = content.match(/[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*/g);
    if (matches) {
      tags.push(...matches.slice(0, 5));
    }
    
    return [...new Set(tags)]; // Remove duplicates
  }

  /**
   * Calculate overall confidence for all findings
   */
  private calculateOverallConfidence(findings: Finding[]): number {
    if (findings.length === 0) return 0;
    
    const totalConfidence = findings.reduce((sum, f) => sum + f.confidence, 0);
    return totalConfidence / findings.length;
  }
}