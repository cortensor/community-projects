type Category = 'general' | 'technology' | 'science' | 'random';

export interface NewsItem {
  title: string;
  url: string;
  source: string;
  publishedAt?: string;
  category?: string;
  description?: string;
}

const NEWS_LIMIT = 6;

const getEnv = (key: string): string => process.env[key] || '';

async function safeJsonFetch<T>(url: string, init?: RequestInit): Promise<T | null> {
  try {
    const res = await fetch(url, init);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch (error) {
    console.warn('news fetch failed', url, error);
    return null;
  }
}

function normalizeSource(src: any, fallback: string): string {
  if (!src) return fallback;
  if (typeof src === 'string') return src;
  if (typeof src === 'object') {
    return src.name || src.id || src.url || fallback;
  }
  return fallback;
}

function mapNewsApiArticles(data: any): NewsItem[] {
  if (!data?.articles) return [];
  return (data.articles as any[])
    .slice(0, NEWS_LIMIT)
    .map((a) => ({
      title: a.title || 'Untitled',
      url: a.url,
      source: normalizeSource(a.source, 'NewsAPI'),
      publishedAt: a.publishedAt,
      description: a.description,
    }))
    .filter((a) => a.url);
}

function mapGNewsArticles(data: any): NewsItem[] {
  if (!data?.articles) return [];
  return (data.articles as any[])
    .slice(0, NEWS_LIMIT)
    .map((a) => ({
      title: a.title || 'Untitled',
      url: a.url,
      source: normalizeSource(a.source, 'GNews'),
      publishedAt: a.publishedAt,
      description: a.description,
    }))
    .filter((a) => a.url);
}

function mapMediastackArticles(data: any): NewsItem[] {
  if (!data?.data) return [];
  return (data.data as any[])
    .slice(0, NEWS_LIMIT)
    .map((a) => ({
      title: a.title || 'Untitled',
      url: a.url || a.source || '',
      source: normalizeSource(a.source, 'Mediastack'),
      publishedAt: a.published_at,
      description: a.description,
    }))
    .filter((a) => a.url);
}

function mapHN(data: any): NewsItem[] {
  if (!data?.hits) return [];
  return (data.hits as any[]).slice(0, NEWS_LIMIT).map((h) => ({
    title: h.title || 'HN story',
    url: h.url || `https://news.ycombinator.com/item?id=${h.objectID}`,
    source: 'Hacker News',
    publishedAt: h.created_at,
  }));
}

function mapReddit(data: any): NewsItem[] {
  const children = data?.data?.children;
  if (!children) return [];
  return children.slice(0, NEWS_LIMIT).map((c: any) => ({
    title: c.data?.title || 'Reddit post',
    url: `https://reddit.com${c.data?.permalink}`,
    source: 'r/technology',
    publishedAt: c.data?.created_utc ? new Date(c.data.created_utc * 1000).toISOString() : undefined,
  }));
}

function parseRssTitles(xml: string, source: string): NewsItem[] {
  const items: NewsItem[] = [];
  const regex = /<item>([\s\S]*?)<\/item>/gim;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(xml)) && items.length < NEWS_LIMIT) {
    const itemXml = match[1];
    const titleMatch = itemXml.match(/<title>([\s\S]*?)<\/title>/i);
    const linkMatch = itemXml.match(/<link>([\s\S]*?)<\/link>/i);
    if (titleMatch && linkMatch) {
      items.push({
        title: decode(titleMatch[1]),
        url: decode(linkMatch[1]),
        source,
      });
    }
  }
  return items;
}

function decode(value: string): string {
  return value
    .replace(/<!\[CDATA\[(.*?)\]\]>/g, '$1')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .trim();
}

async function fetchWikipediaRandom(): Promise<NewsItem[]> {
  const data = await safeJsonFetch<any>('https://en.wikipedia.org/api/rest_v1/page/random/summary');
  if (!data) return [];
  return [{
    title: data.title || 'Random Article',
    url: data.content_urls?.desktop?.page || data.content_urls?.mobile?.page || '',
    source: 'Wikipedia',
    description: data.extract,
  }].filter((a) => a.url);
}

async function fetchPublicApisNews(): Promise<NewsItem[]> {
  const data = await safeJsonFetch<any>('https://api.publicapis.org/entries?category=News');
  if (!data?.entries) return [];
  return (data.entries as any[]).slice(0, NEWS_LIMIT).map((e) => ({
    title: e.API,
    url: e.Link,
    source: e.Category || 'Public APIs',
    description: e.Description,
  })).filter((a) => a.url);
}

async function fetchScienceSpotlight(nasaKey: string): Promise<NewsItem[]> {
  const items: NewsItem[] = [];
  const nasa = await safeJsonFetch<any>(`https://api.nasa.gov/planetary/apod?api_key=${nasaKey || 'DEMO_KEY'}`);
  if (nasa?.url) {
    items.push({
      title: nasa.title || 'NASA Astronomy Picture of the Day',
      url: nasa.hdurl || nasa.url,
      source: 'NASA APOD',
      description: nasa.explanation,
      publishedAt: nasa.date,
    });
  }
  const arxivRes = await fetch('http://export.arxiv.org/api/query?search_query=cat:cs.AI&start=0&max_results=5');
  if (arxivRes.ok) {
    const xml = await arxivRes.text();
    const entryRegex = /<entry>[\s\S]*?<title>([\s\S]*?)<\/title>[\s\S]*?<id>([\s\S]*?)<\/id>/gim;
    let match: RegExpExecArray | null;
    while ((match = entryRegex.exec(xml)) && items.length < NEWS_LIMIT) {
      items.push({
        title: decode(match[1]),
        url: decode(match[2]),
        source: 'arXiv cs.AI',
      });
    }
  }
  return items;
}

export async function fetchNews(category: Category): Promise<NewsItem[]> {
  const newsApiKey = getEnv('NEWSAPI_API_KEY');
  const gnewsKey = getEnv('GNEWS_API_KEY');
  const mediastackKey = getEnv('MEDIASTACK_API_KEY');
  const nasaKey = getEnv('NASA_API_KEY');

  if (category === 'random') {
    return fetchWikipediaRandom();
  }

  if (category === 'science') {
    return fetchScienceSpotlight(nasaKey);
  }

  if (category === 'technology') {
    const [hn, devTo, reddit] = await Promise.all([
      safeJsonFetch<any>('https://hn.algolia.com/api/v1/search?tags=front_page'),
      (async () => {
        try {
          const res = await fetch('https://dev.to/feed');
          if (!res.ok) return null;
          const xml = await res.text();
          return parseRssTitles(xml, 'Dev.to');
        } catch (error) {
          console.warn('dev.to fetch failed', error);
          return null;
        }
      })(),
      safeJsonFetch<any>('https://www.reddit.com/r/technology/.json')
    ]);

    const list: NewsItem[] = [];
    if (hn) list.push(...mapHN(hn));
    if (Array.isArray(devTo)) list.push(...devTo);
    if (reddit) list.push(...mapReddit(reddit));
    return list.slice(0, NEWS_LIMIT);
  }

  // Default/general news: try NewsAPI, GNews, then Mediastack
  if (newsApiKey) {
    const data = await safeJsonFetch<any>(`https://newsapi.org/v2/top-headlines?country=id&pageSize=${NEWS_LIMIT}&apiKey=${newsApiKey}`);
    const mapped = mapNewsApiArticles(data);
    if (mapped.length) return mapped;
  }
  if (gnewsKey) {
    const data = await safeJsonFetch<any>(`https://gnews.io/api/v4/top-headlines?lang=en&max=${NEWS_LIMIT}&token=${gnewsKey}`);
    const mapped = mapGNewsArticles(data);
    if (mapped.length) return mapped;
  }
  if (mediastackKey) {
    const data = await safeJsonFetch<any>(`http://api.mediastack.com/v1/news?access_key=${mediastackKey}&countries=us,id&limit=${NEWS_LIMIT}`);
    const mapped = mapMediastackArticles(data);
    if (mapped.length) return mapped;
  }

  // Fallback to Wikipedia random if everything fails
  return fetchWikipediaRandom();
}
