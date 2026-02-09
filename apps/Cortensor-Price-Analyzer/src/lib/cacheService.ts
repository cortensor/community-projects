/**
 * Simple in-memory cache with TTL support for market data.
 * Reduces API calls and improves response times.
 */

interface CacheEntry<T> {
  data: T;
  expiresAt: number;
  createdAt: number;
}

interface CacheStats {
  hits: number;
  misses: number;
  size: number;
}

type CacheTTL = {
  /** Equities: 5 minutes */
  equity: number;
  /** ETFs: 5 minutes */
  etf: number;
  /** Crypto: 2 minutes (more volatile) */
  crypto: number;
  /** Forex: 3 minutes */
  forex: number;
  /** Commodities: 5 minutes */
  commodity: number;
  /** News: 10 minutes */
  news: number;
  /** AI Analysis: 15 minutes */
  ai: number;
  /** Default: 5 minutes */
  default: number;
};

const DEFAULT_TTL: CacheTTL = {
  equity: 5 * 60 * 1000,
  etf: 5 * 60 * 1000,
  crypto: 2 * 60 * 1000,
  forex: 3 * 60 * 1000,
  commodity: 5 * 60 * 1000,
  news: 10 * 60 * 1000,
  ai: 15 * 60 * 1000,
  default: 5 * 60 * 1000,
};

class CacheService {
  private cache: Map<string, CacheEntry<unknown>> = new Map();
  private stats: CacheStats = { hits: 0, misses: 0, size: 0 };
  private maxSize: number;
  private ttlConfig: CacheTTL;

  constructor(maxSize = 500, ttlConfig: Partial<CacheTTL> = {}) {
    this.maxSize = maxSize;
    this.ttlConfig = { ...DEFAULT_TTL, ...ttlConfig };
  }

  /**
   * Generate cache key from components
   */
  generateKey(prefix: string, ...parts: (string | number | undefined)[]): string {
    const sanitized = parts
      .filter((p): p is string | number => p !== undefined)
      .map((p) => String(p).toLowerCase().trim())
      .join(':');
    return `${prefix}:${sanitized}`;
  }

  /**
   * Get item from cache if valid
   */
  get<T>(key: string): T | null {
    const entry = this.cache.get(key) as CacheEntry<T> | undefined;
    
    if (!entry) {
      this.stats.misses++;
      return null;
    }

    if (Date.now() > entry.expiresAt) {
      this.cache.delete(key);
      this.stats.misses++;
      this.stats.size = this.cache.size;
      return null;
    }

    this.stats.hits++;
    return entry.data;
  }

  /**
   * Set item in cache with TTL
   */
  set<T>(key: string, data: T, ttlType: keyof CacheTTL = 'default'): void {
    // Evict oldest entries if at capacity
    if (this.cache.size >= this.maxSize) {
      this.evictOldest(Math.ceil(this.maxSize * 0.1));
    }

    const ttl = this.ttlConfig[ttlType];
    const now = Date.now();

    this.cache.set(key, {
      data,
      createdAt: now,
      expiresAt: now + ttl,
    });

    this.stats.size = this.cache.size;
  }

  /**
   * Check if key exists and is valid
   */
  has(key: string): boolean {
    const entry = this.cache.get(key);
    if (!entry) return false;
    if (Date.now() > entry.expiresAt) {
      this.cache.delete(key);
      this.stats.size = this.cache.size;
      return false;
    }
    return true;
  }

  /**
   * Delete specific key
   */
  delete(key: string): boolean {
    const result = this.cache.delete(key);
    this.stats.size = this.cache.size;
    return result;
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.cache.clear();
    this.stats.size = 0;
  }

  /**
   * Clear expired entries
   */
  prune(): number {
    const now = Date.now();
    let pruned = 0;

    for (const [key, entry] of this.cache.entries()) {
      if (now > entry.expiresAt) {
        this.cache.delete(key);
        pruned++;
      }
    }

    this.stats.size = this.cache.size;
    return pruned;
  }

  /**
   * Get cache statistics
   */
  getStats(): CacheStats & { hitRate: number } {
    const total = this.stats.hits + this.stats.misses;
    return {
      ...this.stats,
      hitRate: total > 0 ? this.stats.hits / total : 0,
    };
  }

  /**
   * Get or fetch with caching
   */
  async getOrFetch<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttlType: keyof CacheTTL = 'default',
  ): Promise<T> {
    const cached = this.get<T>(key);
    if (cached !== null) {
      return cached;
    }

    const data = await fetcher();
    this.set(key, data, ttlType);
    return data;
  }

  /**
   * Evict oldest entries
   */
  private evictOldest(count: number): void {
    const entries = Array.from(this.cache.entries())
      .sort((a, b) => a[1].createdAt - b[1].createdAt)
      .slice(0, count);

    for (const [key] of entries) {
      this.cache.delete(key);
    }

    this.stats.size = this.cache.size;
  }
}

// Singleton instance for app-wide caching
export const marketCache = new CacheService(500);

// Export class for testing or custom instances
export { CacheService };
export type { CacheTTL, CacheStats };
