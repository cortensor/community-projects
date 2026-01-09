import { NextRequest } from 'next/server';
import { URLFetcher } from '@/lib/urlFetcher';
import { CortensorService } from '@/lib/cortensorService';
import { SearchService } from '@/lib/searchService';
import { debugLog } from '@/lib/env';
import { upsertHistoryItem } from '@/lib/historyDb';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function filterDeepSeekOutput(text: string): string {
  if (!text) return '';
  let cleaned = text.replace(/<think>[\s\S]*?<\/think>/gi, '');
  const thinkEndIndex = text.toLowerCase().lastIndexOf('</think>');
  if (thinkEndIndex !== -1) {
    cleaned = text.substring(thinkEndIndex + 8).trim();
  }
  cleaned = cleaned
    .replace(/｜end▁of▁sentence｜/g, '')
    .replace(/\<\|end▁of▁sentence\|\>/g, '')
    .replace(/▁+/g, ' ')
    .replace(/▁/g, ' ')
    .trim();
  return cleaned;
}

function processSummaryResponse(summaryData: { summary?: string; keyPoints?: string[]; wasEnriched?: boolean }) {
  let summary = summaryData.summary || '';
  let keyPoints: string[] = [];

  summary = filterDeepSeekOutput(summary);

  const keyInsightsMatch = summary.match(/\*\*KEY INSIGHTS?\*\*:?(\s*)([\s\S]*?)(?=\n\n|\*\*ADDITIONAL|$)/i) ||
    summary.match(/KEY INSIGHTS?\s*:?(\s*)([\s\S]*?)(?=\n\n|\*\*ADDITIONAL|$)/i);

  if (keyInsightsMatch) {
    const keyInsightsText = keyInsightsMatch[2];
    const bulletSplit = keyInsightsText.split(/\s*•\s*/).filter(part => part.trim().length > 10);

    if (bulletSplit.length > 1) {
      if (bulletSplit[0].trim().length < 50 || !bulletSplit[0].includes('.')) {
        bulletSplit.shift();
      }

      keyPoints = bulletSplit.map(point => point.trim()
        .replace(/^\s*[\-\*•]\s*/, '')
        .replace(/\s+/g, ' ')
        .trim()).filter(point => point.length > 15);
    } else {
      const bulletPoints = keyInsightsText.match(/(?:^|\n)[\s]*(?:[-•*]|\d+\.)\s*(.+)/gm);
      if (bulletPoints && bulletPoints.length > 0) {
        keyPoints = bulletPoints.map(point => point.replace(/^[\s]*(?:[-•*]|\d+\.)\s*/, '').trim()).filter(point => point.length > 10);
      } else {
        const sentences = keyInsightsText.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 20);
        if (sentences.length > 1) {
          keyPoints = sentences.map(s => s.trim()).filter(Boolean);
        }
      }
    }

    summary = summary.replace(/\*\*KEY INSIGHTS?\*\*:?[\s\S]*?(?=\n\n|\*\*ADDITIONAL|$)/i, '').trim();
    summary = summary.replace(/KEY INSIGHTS?\s*:?[\s\S]*?(?=\n\n|\*\*ADDITIONAL|$)/i, '').trim();
  }

  if (keyPoints.length === 0 && summaryData.keyPoints) {
    keyPoints = Array.isArray(summaryData.keyPoints) ? summaryData.keyPoints : [];
  }

  summary = summary
    .replace(/\*\*KEY INSIGHTS?\*\*/gi, '')
    .replace(/^KEY INSIGHTS?:?\s*/gmi, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  const wordCount = summary.split(/\s+/).filter(Boolean).length;

  return { summary, keyPoints, wordCount, wasEnriched: summaryData.wasEnriched || false };
}

function buildClientReference(rawUserId: unknown): string {
  const raw = typeof rawUserId === 'string' ? rawUserId.trim() : '';
  const cleaned = raw.replace(/[^a-zA-Z0-9_-]/g, '');
  const baseId = cleaned.length > 0 ? cleaned : `session-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
  return baseId.startsWith('user-summarizer-') ? baseId : `user-summarizer-${baseId}`;
}

function nowMs(): number {
  // perf_hooks isn't necessary; Date.now is fine for UX durations
  return Date.now();
}

export async function POST(request: NextRequest) {
  const encoder = new TextEncoder();

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const send = (event: string, data: any) => {
        controller.enqueue(encoder.encode(`event: ${event}\n`));
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
      };

      const stepOrder = ['validate', 'extract', 'prepare', 'summarize', 'insights', 'quality', 'enrich', 'finalize'] as const;
      const stepIndex = (id: string) => Math.max(0, stepOrder.indexOf(id as any));
      const progressFor = (id: string) => Math.round(((stepIndex(id) + 1) / stepOrder.length) * 100);

      const stepStart: Record<string, number> = {};
      const beginStep = (id: string) => {
        stepStart[id] = nowMs();
        send('step', { id, status: 'active', progress: progressFor(id) });
      };
      const completeStep = (id: string) => {
        const durationMs = Math.max(0, nowMs() - (stepStart[id] ?? nowMs()));
        send('step', { id, status: 'completed', duration: `${(durationMs / 1000).toFixed(1)}s`, progress: progressFor(id) });
      };
      const errorStep = (id: string, message: string) => {
        send('step', { id, status: 'error', progress: progressFor(id) });
        send('error', { message });
      };

      try {
        const { url, userId } = await request.json();

        beginStep('validate');
        if (!url || typeof url !== 'string') {
          errorStep('validate', 'URL is required');
          controller.close();
          return;
        }
        // validate URL format
        try {
          new URL(url);
        } catch {
          errorStep('validate', 'Invalid URL');
          controller.close();
          return;
        }
        completeStep('validate');

        beginStep('extract');
        const urlFetcher = new URLFetcher();
        let article;
        try {
          article = await urlFetcher.fetchArticle(url);
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Failed to fetch article';
          errorStep('extract', message);
          controller.close();
          return;
        }
        if (!article || !article.content) {
          errorStep('extract', 'Failed to extract content from URL');
          controller.close();
          return;
        }
        completeStep('extract');

        beginStep('prepare');
        // placeholder for future: chunking / compression decisions are inside CortensorService
        completeStep('prepare');

        beginStep('summarize');
        const clientReference = buildClientReference(userId);

        const searchService = new SearchService();
        // search can take time too; we keep it under summarize step for now
        const searchResults = await searchService.searchAdditionalSources(
          article.title || 'research topic',
          [],
          article.url
        );

        const cortensorService = new CortensorService();
        let summaryResult;
        try {
          summaryResult = await cortensorService.generateSummary(article, clientReference);
          if (summaryResult.needsEnrichment && searchResults.length > 0) {
            summaryResult = await cortensorService.enrichSummary(summaryResult, searchResults, `${clientReference}-enrich`);
          }
        } catch (err) {
          debugLog('Cortensor API Error:', err);
          errorStep('summarize', 'Failed to generate summary with AI service');
          controller.close();
          return;
        }
        completeStep('summarize');

        beginStep('insights');
        const processedSummary = processSummaryResponse(summaryResult);
        completeStep('insights');

        beginStep('quality');
        // future: quality scoring; for now mark completed
        completeStep('quality');

        beginStep('enrich');
        if (summaryResult.needsEnrichment || summaryResult.wasEnriched) {
          // already applied during summarize; mark as completed
          completeStep('enrich');
        } else {
          send('step', { id: 'enrich', status: 'completed', duration: 'Skipped', progress: progressFor('enrich') });
        }

        beginStep('finalize');

        const resultData = {
          article: {
            title: article.title,
            author: article.author,
            publishDate: article.publishDate,
            url: article.url,
          },
          summary: processedSummary.summary,
          keyPoints: processedSummary.keyPoints,
          wordCount: processedSummary.wordCount,
          wasEnriched: processedSummary.wasEnriched,
          needsEnrichment: summaryResult.needsEnrichment,
          contentTruncated: summaryResult.sourceTruncated ?? false,
          originalContentLength: summaryResult.originalContentLength ?? article.content.length,
          submittedContentLength: summaryResult.submittedContentLength ?? article.content.length,
          compressionMethod: summaryResult.compressionMethod ?? 'pass-through',
        };

        // Persist to DB (best-effort; tied to userId if present)
        const userIdString = typeof userId === 'string' ? userId.trim() : '';
        if (userIdString) {
          try {
            upsertHistoryItem(userIdString, {
              timestamp: Date.now(),
              url: resultData.article.url,
              title: resultData.article.title,
              author: resultData.article.author ?? undefined,
              publishDate: resultData.article.publishDate ?? undefined,
              summary: resultData.summary,
              keyPoints: resultData.keyPoints,
              wordCount: resultData.wordCount,
              wasEnriched: !!resultData.wasEnriched,
            });
          } catch (dbErr) {
            debugLog('History DB write failed:', dbErr);
          }
        }

        completeStep('finalize');

        send('result', { success: true, data: resultData });
        send('done', { ok: true });
        controller.close();
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Internal server error';
        send('error', { message });
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
    },
  });
}
