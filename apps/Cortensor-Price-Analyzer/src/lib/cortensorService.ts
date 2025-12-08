import axios, { type AxiosError } from 'axios';
import type { AIAnalysis, CatalystHighlight, MarketAnalysisContext, MarketNewsItem } from './marketTypes';

interface CortensorChoiceResponse {
  text?: string;
}

interface CortensorApiResponse {
  choices?: CortensorChoiceResponse[];
  text?: string;
}

const DEFAULT_CONFIDENCE = 'medium';

export class CortensorService {
  private readonly apiKey: string;
  private readonly apiUrl: string;
  private readonly sessionId: number;
  private readonly temperature: number;
  private readonly maxTokens: number;
  private readonly timeoutMs: number;
  private readonly retryTimeoutMs: number;

  constructor() {
    this.apiKey = process.env.CORTENSOR_API_KEY ?? '';
    if (!this.apiKey) {
      throw new Error('CORTENSOR_API_KEY is required');
    }

    const baseUrl = process.env.CORTENSOR_BASE_URL ?? 'http://69.164.253.134:5010';
    const explicitUrl = process.env.CORTENSOR_API_URL;
    this.apiUrl = explicitUrl
      ? explicitUrl.trim().replace(/\/$/, '')
      : `${baseUrl.replace(/\/$/, '')}/api/v1/completions`;

    const sessionEnv =
      process.env.CORTENSOR_SESSION_ID ?? process.env.CORTENSOR_SESSION ?? process.env.CORTENSOR_SESSIONID ?? '6';
  const parsedSession = Number.parseInt(sessionEnv, 10);
  this.sessionId = Number.isFinite(parsedSession) ? parsedSession : 6;
    this.temperature = Number.parseFloat(process.env.CORTENSOR_TEMPERATURE ?? '0.35');
    this.maxTokens = Number.parseInt(process.env.CORTENSOR_MAX_TOKENS ?? '2800', 10);
    const timeoutSeconds = Number.parseInt(process.env.CORTENSOR_TIMEOUT ?? '45', 10);
    this.timeoutMs = Number.isFinite(timeoutSeconds) ? timeoutSeconds * 1000 : 45_000;
    const retrySeconds = Number.parseInt(process.env.CORTENSOR_RETRY_TIMEOUT ?? '20', 10);
    this.retryTimeoutMs = Number.isFinite(retrySeconds) ? retrySeconds * 1000 : 20_000;
  }

  async generatePriceAnalysis(context: MarketAnalysisContext): Promise<AIAnalysis> {
    const prompt = this.buildPrompt(context);

    try {
      const raw = await this.requestWithRetry(prompt);
      return this.parseResponse(raw, context);
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const descriptor = this.describeAxiosError(error);
        console.warn(`Cortensor price analysis degraded: ${descriptor}`);
        const fallbackNarrative = `${this.composeFallbackNarrative(context)} (AI narrative unavailable — ${descriptor}).`;
        return this.fallbackAnalysis(context, fallbackNarrative);
      }

      console.error('Cortensor price analysis error:', error);
      return this.fallbackAnalysis(context, this.composeFallbackNarrative(context));
    }
  }

  private async requestWithRetry(prompt: string): Promise<string> {
    const attempts = [
      { maxTokens: this.maxTokens, timeout: this.timeoutMs },
      { maxTokens: Math.max(512, Math.round(this.maxTokens * 0.6)), timeout: this.retryTimeoutMs },
    ];

    let lastError: unknown;
    for (let index = 0; index < attempts.length; index += 1) {
      const attempt = attempts[index];
      try {
        const response = await axios.post<CortensorApiResponse>(
          this.apiUrl,
          {
            session_id: this.sessionId,
            prompt,
            stream: false,
            temperature: this.temperature,
            max_tokens: attempt.maxTokens,
          },
          {
            headers: {
              Authorization: `Bearer ${this.apiKey}`,
              'Content-Type': 'application/json',
            },
            timeout: attempt.timeout,
          },
        );

        const raw = response.data?.choices?.[0]?.text ?? response.data?.text ?? '';
        if (raw.trim().length === 0) {
          throw new Error('Empty Cortensor response');
        }
        return raw;
      } catch (error) {
        lastError = error;
        if (!axios.isAxiosError(error) || !this.isRetriableError(error) || index === attempts.length - 1) {
          throw error;
        }

        const descriptor = this.describeAxiosError(error);
        console.warn(`Cortensor request attempt ${index + 1} failed (${descriptor}); retrying with lighter payload.`);
        await this.delay(1_000 * (index + 1));
      }
    }

    throw lastError;
  }

  private buildPrompt(context: MarketAnalysisContext): string {
    const { snapshot, technicals, fundamentals, catalysts, news, horizon } = context;

    const technicalHighlights = [
      `RSI14: ${technicals.rsi14?.toFixed(1) ?? 'n/a'}`,
      `MACD: ${technicals.macd?.toFixed(2) ?? 'n/a'} (signal ${technicals.macdSignal?.toFixed(2) ?? 'n/a'})`,
      `SMA20/50/200: ${technicals.sma20?.toFixed(2) ?? '—'} / ${technicals.sma50?.toFixed(2) ?? '—'} / ${
        technicals.sma200?.toFixed(2) ?? '—'
      }`,
      `Volatility (ann.): ${technicals.volatility ? `${(technicals.volatility * 100).toFixed(1)}%` : 'n/a'}`,
      `Volume trend: ${technicals.volumeTrend?.toFixed(2) ?? 'n/a'}`,
    ].join('\n');

    const fundamentalHighlights = [
      `Market Cap: ${fundamentals.marketCap ?? 'n/a'}`,
      `P/E: ${fundamentals.peRatio?.toFixed(2) ?? 'n/a'}`,
      `P/B: ${fundamentals.pbRatio?.toFixed(2) ?? 'n/a'}`,
      `Dividend Yield: ${fundamentals.dividendYield ? `${(fundamentals.dividendYield * 100).toFixed(2)}%` : 'n/a'}`,
      `Revenue Growth: ${
        fundamentals.revenueGrowth ? `${(fundamentals.revenueGrowth * 100).toFixed(1)}%` : 'n/a'
      }`,
      `Margins (Gross/Op/Net): ${[
        fundamentals.grossMargin,
        fundamentals.operatingMargin,
        fundamentals.netMargin,
      ]
        .map((value) => (value ? `${(value * 100).toFixed(1)}%` : '—'))
        .join('/')}`,
    ].join('\n');

    const catalystHighlights = catalysts.length
      ? catalysts
          .map((catalyst: CatalystHighlight) =>
            `- ${catalyst.label}${catalyst.impact ? ` (${catalyst.impact})` : ''}: ${catalyst.description}`,
          )
          .join('\n')
      : 'None detected.';

    const newsHighlights = news.length
      ? news
          .slice(0, 6)
          .map(
            (item: MarketNewsItem) =>
              `- [${item.sentiment?.toUpperCase() ?? 'NEUTRAL'}] ${item.title} (${item.source}, ${item.publishedAt})`,
          )
          .join('\n')
      : 'No relevant headlines retrieved.';

    return `You are an institutional-grade market strategist. Produce a concise but comprehensive price analysis using the provided market context.

Return ONLY valid JSON that conforms to this TypeScript type (do not include markdown fences):
{
  "narrative": string; // 3–4 sentences blending technical, fundamental, and narrative color.
  "keyPoints": string[]; // 4-6 bullet-ready takeaways.
  "opportunities": string[]; // potential upside catalysts or setups.
  "risks": string[]; // key downside scenarios or watch-outs.
  "nextSteps": string[]; // optional follow-up actions for an analyst or trader.
  "confidence": "low" | "medium" | "high"; // qualitative confidence in the narrative.
  "horizonNote": string; // comment on the ${horizon} horizon outlook.
}

ASSET SNAPSHOT
Ticker: ${snapshot.ticker}
Asset Type: ${snapshot.assetType}
Company: ${snapshot.companyName ?? 'n/a'}
Exchange: ${snapshot.exchange ?? 'n/a'}
Currency: ${snapshot.currency ?? 'USD'}
Latest Price: ${snapshot.latestPrice ?? 'n/a'}
Change: ${snapshot.change ?? 'n/a'} (${snapshot.changePercent ?? 'n/a'}%)
Volume: ${snapshot.volume ?? 'n/a'} vs Avg ${snapshot.averageVolume ?? 'n/a'}

TECHNICALS
${technicalHighlights}

FUNDAMENTALS
${fundamentalHighlights}

CATALYSTS
${catalystHighlights}

NEWS (freshest first)
${newsHighlights}

GUIDELINES
- Be decisive and avoid hedging language.
- Quantify each insight with the data provided.
- Connect technical, fundamental, and news factors.
- Emphasize what matters over the next ${horizon}.
- Output MUST be valid JSON.`;
  }

  private parseResponse(raw: string, context: MarketAnalysisContext): AIAnalysis {
    const cleaned = raw.trim();
    const jsonCandidate = this.extractJson(cleaned);

    if (jsonCandidate) {
      try {
        const parsed = JSON.parse(jsonCandidate) as Partial<AIAnalysis>;
        return this.normalizeAnalysis(parsed, context);
      } catch (error) {
        console.warn('Failed to parse Cortensor JSON payload:', error);
      }
    }

    const fallbackNarrative = cleaned
      .replace(/^[^{]*\{/, '{')
      .replace(/\}(?!.*\})[\s\S]*$/, '}')
      .trim();

    return this.fallbackAnalysis(context, fallbackNarrative || 'AI response was empty.');
  }

  private normalizeAnalysis(partial: Partial<AIAnalysis>, context: MarketAnalysisContext): AIAnalysis {
    const ensureStringArray = (value: unknown, min: number, fallback: string[]): string[] => {
      if (Array.isArray(value)) {
        const filtered = value
          .map((item) => (typeof item === 'string' ? item.trim() : ''))
          .filter((item) => item.length > 0);
        if (filtered.length >= min) return filtered;
      }
      return fallback;
    };

    const narrative = typeof partial.narrative === 'string' && partial.narrative.trim().length > 0
      ? partial.narrative.trim()
      : this.composeFallbackNarrative(context);

    return {
      narrative,
      keyPoints: ensureStringArray(partial.keyPoints, 3, this.deriveKeyPoints(context)),
      opportunities: ensureStringArray(partial.opportunities, 0, this.deriveOpportunities(context)),
      risks: ensureStringArray(partial.risks, 0, this.deriveRisks(context)),
      nextSteps: ensureStringArray(partial.nextSteps, 0, []),
      confidence: this.normalizeConfidence(partial.confidence),
      horizonNote:
        typeof partial.horizonNote === 'string' && partial.horizonNote.trim().length > 0
          ? partial.horizonNote.trim()
          : `Outlook calibrated for the ${context.horizon} horizon.`,
    };
  }

  private normalizeConfidence(value: unknown): 'low' | 'medium' | 'high' {
    if (value === 'low' || value === 'medium' || value === 'high') {
      return value;
    }
    return DEFAULT_CONFIDENCE;
  }

  private extractJson(text: string): string | null {
    const start = text.indexOf('{');
    const end = text.lastIndexOf('}');
    if (start === -1 || end === -1 || end <= start) {
      return null;
    }
    const candidate = text.slice(start, end + 1);
    return candidate.trim().length > 0 ? candidate : null;
  }

  private fallbackAnalysis(context: MarketAnalysisContext, narrative: string): AIAnalysis {
    return {
      narrative,
      keyPoints: this.deriveKeyPoints(context),
      opportunities: this.deriveOpportunities(context),
      risks: this.deriveRisks(context),
      nextSteps: [],
      confidence: DEFAULT_CONFIDENCE,
      horizonNote: `Insights inferred for the ${context.horizon} horizon using available data.`,
    };
  }

  private composeFallbackNarrative(context: MarketAnalysisContext): string {
    const { snapshot, technicals, fundamentals } = context;
    const parts: string[] = [];

    parts.push(
      `${snapshot.ticker} ${snapshot.companyName ? `(${snapshot.companyName})` : ''} trades at ${
        snapshot.latestPrice !== undefined ? `$${snapshot.latestPrice.toFixed(2)}` : 'an unavailable price'
      } with ${snapshot.changePercent ? `${snapshot.changePercent.toFixed(2)}%` : 'muted'} daily moves.`,
    );

    if (technicals.rsi14) {
      parts.push(`Momentum screens show RSI near ${technicals.rsi14.toFixed(1)}, framing near-term positioning.`);
    }
    if (fundamentals.peRatio) {
      parts.push(`Valuation prints a P/E of ${fundamentals.peRatio.toFixed(1)}, anchoring the fundamental view.`);
    }

    return parts.join(' ');
  }

  private deriveKeyPoints(context: MarketAnalysisContext): string[] {
    const points: string[] = [];
    const { snapshot, technicals, fundamentals, catalysts } = context;

    if (snapshot.changePercent !== undefined) {
      points.push(
        `${snapshot.ticker} moved ${snapshot.changePercent >= 0 ? '+' : ''}${snapshot.changePercent.toFixed(
          2,
        )}% on ${snapshot.volume ? `${this.formatNumber(snapshot.volume)} shares` : 'muted volume'}.`,
      );
    }
    if (technicals.rsi14) {
      points.push(`RSI sits at ${technicals.rsi14.toFixed(1)}, signalling ${technicals.rsi14 > 60 ? 'overbought' : 'neutral'} momentum.`);
    }
    if (fundamentals.marketCap) {
      points.push(`Market cap registers ${this.formatNumber(fundamentals.marketCap)}, supporting liquidity assumptions.`);
    }
    if (catalysts.length > 0) {
      points.push(`Key catalyst: ${catalysts[0].label}${catalysts[0].impact ? ` (${catalysts[0].impact})` : ''}.`);
    }

    return points.slice(0, 5);
  }

  private deriveOpportunities(context: MarketAnalysisContext): string[] {
    const items: string[] = [];
    const { technicals, catalysts } = context;

    if (technicals.supportLevel && technicals.resistanceLevel) {
      items.push(
        `Range insight: support near ${technicals.supportLevel.toFixed(2)} versus resistance around ${
          technicals.resistanceLevel.toFixed(2)
        }.`,
      );
    }
    catalysts
      .filter((catalyst: CatalystHighlight) => catalyst.impact !== 'low')
      .forEach((catalyst: CatalystHighlight) => items.push(`Catalyst — ${catalyst.label}: ${catalyst.description}`));

    return items.slice(0, 4);
  }

  private deriveRisks(context: MarketAnalysisContext): string[] {
    const items: string[] = [];
    const { technicals, news } = context;

    if (technicals.volatility && technicals.volatility > 0.35) {
      items.push(`Realised volatility north of ${(technicals.volatility * 100).toFixed(1)}% heightens positioning risk.`);
    }

    news
      .filter((item: MarketNewsItem) => item.sentiment === 'negative')
      .slice(0, 2)
      .forEach((item: MarketNewsItem) => items.push(`Headline risk: ${item.title} (${item.source}).`));

    return items.slice(0, 4);
  }

  private formatNumber(value: number): string {
    if (Math.abs(value) >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
    if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
    return value.toFixed(0);
  }

  private describeAxiosError(error: unknown): string {
    if (!axios.isAxiosError(error)) {
      return 'unknown error';
    }

    const status = error.response?.status;
    const message = (error.response?.data as { error?: string } | undefined)?.error ?? error.message;
    if (status) {
      return `${status} ${message}`;
    }
    if (error.code) {
      return `${error.code} ${message}`;
    }
    return message;
  }

  private isRetriableError(error: AxiosError): boolean {
    if (!error) {
      return false;
    }
    const retriableStatuses = new Set([408, 429, 502, 503, 504]);
    if (error.response?.status && retriableStatuses.has(error.response.status)) {
      return true;
    }
    return error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT';
  }

  private delay(durationMs: number): Promise<void> {
    return new Promise((resolve) => {
      setTimeout(resolve, durationMs);
    });
  }
}