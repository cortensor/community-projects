import { NextRequest, NextResponse } from 'next/server';
import { URLFetcher } from '@/lib/urlFetcher';
import { CortensorService } from '@/lib/cortensorService';
import { SearchService } from '@/lib/searchService';

// Function to filter DeepSeek thinking process and extract only the actual response
function filterDeepSeekOutput(text: string): string {
  if (!text) return '';
  
  console.log('🧠 Raw DeepSeek output length:', text.length);
  
  // Remove <think>...</think> blocks
  let cleaned = text.replace(/<think>[\s\S]*?<\/think>/gi, '');
  
  // If there's a </think> tag, take everything after it
  const thinkEndIndex = text.toLowerCase().lastIndexOf('</think>');
  if (thinkEndIndex !== -1) {
    cleaned = text.substring(thinkEndIndex + 8).trim(); // 8 = length of '</think>'
    console.log('🎯 Found </think> tag, extracted content after it');
  } else {
    console.log('ℹ️ No </think> tag found, using cleaned text');
  }
  
  // Clean up any remaining artifacts
  cleaned = cleaned
    .replace(/｜end▁of▁sentence｜/g, '')
    .replace(/\<\|end▁of▁sentence\|\>/g, '')
    .replace(/▁+/g, ' ')
    .replace(/▁/g, ' ')
    .trim();
    
  console.log('✅ Filtered output length:', cleaned.length);
  return cleaned;
}

function processSummaryResponse(summaryData: { summary?: string; keyPoints?: string[]; wasEnriched?: boolean }) {
  let summary = summaryData.summary || '';
  let keyPoints: string[] = [];
  let wordCount = 0;
  const wasEnriched = summaryData.wasEnriched || false;

  // First, filter out DeepSeek thinking process
  summary = filterDeepSeekOutput(summary);

  // Look for KEY INSIGHTS section with more flexible patterns
  const keyInsightsMatch = summary.match(/\*\*KEY INSIGHTS?\*\*:?\s*([\s\S]*?)(?=\n\n|\*\*ADDITIONAL|$)/i) ||
                          summary.match(/KEY INSIGHTS?\s*:?\s*([\s\S]*?)(?=\n\n|\*\*ADDITIONAL|$)/i);
  
  if (keyInsightsMatch) {
    const keyInsightsText = keyInsightsMatch[1];
    console.log('🔍 Found key insights text:', keyInsightsText.substring(0, 200) + '...');
    
    // Split by bullet points first - look for • followed by text
    const bulletSplit = keyInsightsText.split(/\s*•\s*/).filter(part => part.trim().length > 10);
    
    if (bulletSplit.length > 1) {
      // Remove the first element if it's not a proper bullet point
      if (bulletSplit[0].trim().length < 50 || !bulletSplit[0].includes('.')) {
        bulletSplit.shift();
      }
      
      keyPoints = bulletSplit.map(point => {
        // Clean up each point
        return point.trim()
          .replace(/^\s*[\-\*•]\s*/, '') // Remove any remaining bullets
          .replace(/\s+/g, ' ') // Normalize whitespace
          .trim();
      }).filter(point => point.length > 15);
      
      console.log('✅ Extracted', keyPoints.length, 'key points from bullet splits');
    } else {
      // Fallback: try other bullet patterns
      const bulletPoints = keyInsightsText.match(/(?:^|\n)[\s]*(?:[-•*]|\d+\.)\s*(.+)/gm);
      
      if (bulletPoints && bulletPoints.length > 0) {
        keyPoints = bulletPoints.map(point => 
          point.replace(/^[\s]*(?:[-•*]|\d+\.)\s*/, '').trim()
        ).filter(point => point.length > 10);
        console.log('✅ Extracted', keyPoints.length, 'key points from regex pattern');
      } else {
        // Last resort: split by sentences that seem like key points
        const sentences = keyInsightsText.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 20);
        if (sentences.length > 1) {
          keyPoints = sentences.map(s => s.trim()).filter(s => s.length > 0);
          console.log('📝 Split into', keyPoints.length, 'sentences as key points');
        }
      }
    }
    
    // Remove KEY INSIGHTS section from summary
    summary = summary.replace(/\*\*KEY INSIGHTS?\*\*:?\s*[\s\S]*?(?=\n\n|\*\*ADDITIONAL|$)/i, '').trim();
    summary = summary.replace(/KEY INSIGHTS?\s*:?\s*[\s\S]*?(?=\n\n|\*\*ADDITIONAL|$)/i, '').trim();
  }

  // If no key points found in summary, try to extract from keyPoints property
  if (keyPoints.length === 0 && summaryData.keyPoints) {
    keyPoints = Array.isArray(summaryData.keyPoints) ? summaryData.keyPoints : [];
  }

  // Clean up summary formatting
  summary = summary
    .replace(/\*\*KEY INSIGHTS?\*\*/gi, '')
    .replace(/^KEY INSIGHTS?:?\s*/gmi, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  wordCount = summary.split(/\s+/).filter(word => word.length > 0).length;

  console.log('📊 Processing result: Summary length:', summary.length, 'Key points:', keyPoints.length);

  return { summary, keyPoints, wordCount, wasEnriched };
}

function buildClientReference(rawUserId: unknown): string {
  const raw = typeof rawUserId === 'string' ? rawUserId.trim() : '';
  const cleaned = raw.replace(/[^a-zA-Z0-9_-]/g, '');
  const baseId = cleaned.length > 0
    ? cleaned
    : `session-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
  return baseId.startsWith('user-summarizer-') ? baseId : `user-summarizer-${baseId}`;
}

export async function POST(request: NextRequest) {
  try {
    const { url, userId } = await request.json();

    if (!url) {
      return NextResponse.json({ error: 'URL is required' }, { status: 400 });
    }

    console.log('Processing URL:', url);

    const clientReference = buildClientReference(userId);
    console.log('Using client reference:', clientReference);

    const urlFetcher = new URLFetcher();
    const article = await urlFetcher.fetchArticle(url);

    if (!article || !article.content) {
      return NextResponse.json({ error: 'Failed to extract content from URL' }, { status: 400 });
    }

    console.log('Article fetched:', {
      title: article.title,
      contentLength: article.content.length,
      author: article.author
    });

    const searchService = new SearchService();
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
        summaryResult = await cortensorService.enrichSummary(
          summaryResult,
          searchResults,
          `${clientReference}-enrich`
        );
      }

    } catch (error) {
      console.error('Cortensor API Error:', error);
      return NextResponse.json({ error: 'Failed to generate summary with AI service' }, { status: 500 });
    }

    const processedSummary = processSummaryResponse(summaryResult);

    return NextResponse.json({
      success: true,
      data: {
        article: {
          title: article.title,
          author: article.author,
          publishDate: article.publishDate,
          url: article.url
        },
        summary: processedSummary.summary,
        keyPoints: processedSummary.keyPoints,
        wordCount: processedSummary.wordCount,
        wasEnriched: processedSummary.wasEnriched,
        needsEnrichment: summaryResult.needsEnrichment,
        contentTruncated: summaryResult.sourceTruncated ?? false,
        originalContentLength: summaryResult.originalContentLength ?? article.content.length,
        submittedContentLength: summaryResult.submittedContentLength ?? article.content.length,
        compressionMethod: summaryResult.compressionMethod ?? 'pass-through'
      }
    });

  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
