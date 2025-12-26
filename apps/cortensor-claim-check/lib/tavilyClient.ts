import { TAVILY_SETTINGS } from '@/config/app';

const truncate = (value: string, limit = 1500) => (value.length > limit ? `${value.slice(0, limit - 3)}...` : value);

interface TavilySearchResult {
  url?: string;
  title?: string;
  content?: string;
}

interface TavilySearchResponse {
  answer?: string;
  results?: TavilySearchResult[];
}

const buildSearchPayload = (targetUrl: string) => ({
  api_key: TAVILY_SETTINGS.apiKey,
  query: `Summarize the factual evidence from ${targetUrl} and note any key statistics or named entities.`,
  search_depth: 'advanced',
  include_answer: true,
  include_images: false,
  max_results: 5,
});

const buildClaimSearchPayload = (query: string) => ({
  api_key: TAVILY_SETTINGS.apiKey,
  query: `Provide reputable sources for fact-checking this claim: ${query}`,
  search_depth: 'advanced',
  include_answer: false,
  include_images: false,
  max_results: 6,
});

const pickBestContent = (response: TavilySearchResponse, targetUrl: string) => {
  if (response.answer?.trim()) {
    return response.answer.trim();
  }

  const directMatch = response.results?.find((result) => result.url?.startsWith(targetUrl));
  if (directMatch?.content?.trim()) {
    return directMatch.content.trim();
  }

  const firstResult = response.results?.find((result) => result.content?.trim());
  return firstResult?.content?.trim() ?? null;
};

export async function summarizeUrlWithTavily(targetUrl: string): Promise<string | null> {
  if (!targetUrl) {
    return null;
  }

  if (!TAVILY_SETTINGS.apiKey) {
    return null;
  }

  try {
    const response = await fetch(TAVILY_SETTINGS.searchUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildSearchPayload(targetUrl)),
    });

    if (!response.ok) {
      return null;
    }

    const payload = (await response.json()) as TavilySearchResponse;
    const summary = pickBestContent(payload, targetUrl);
    return summary ? truncate(summary) : null;
  } catch (error) {
    console.warn('[Tavily] Failed to hydrate context URL', error);
    return null;
  }
}

export async function searchCitationsWithTavily(query: string): Promise<
  Array<{ source: string; url: string; description?: string | null }>
> {
  if (!query?.trim()) {
    return [];
  }

  if (!TAVILY_SETTINGS.apiKey) {
    return [];
  }

  try {
    const response = await fetch(TAVILY_SETTINGS.searchUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildClaimSearchPayload(query.trim())),
    });

    if (!response.ok) {
      return [];
    }

    const payload = (await response.json()) as TavilySearchResponse;
    const results = payload.results ?? [];

    return results
      .map((item, idx) => {
        const url = item.url?.trim();
        if (!url) return null;
        const source = item.title?.trim() || item.url?.trim() || `Tavily result ${idx + 1}`;
        const description = item.content?.trim() || payload.answer?.trim() || null;
        return { source, url, description: description ? truncate(description, 280) : null };
      })
      .filter(Boolean) as Array<{ source: string; url: string; description?: string | null }>;
  } catch (error) {
    console.warn('[Tavily] Claim search failed', error);
    return [];
  }
}
