import axios from 'axios';

export interface ArticleContent {
  title: string;
  content: string;
  url: string;
  author?: string;
  publishDate?: string;
}

export class URLFetcher {
  private static pdfParseLoader?: Promise<((data: Uint8Array | ArrayBuffer | Buffer | string | URL | number[]) => Promise<{ text: string; info?: { Title?: string; Author?: string } | undefined }>) | null>;

  async fetchArticle(url: string): Promise<ArticleContent> {
    try {
      // Validate URL
      const parsedUrl = new URL(url);
      const requestTimeout = parseInt(process.env.ARTICLE_FETCH_TIMEOUT || '60000', 10);

      const response = await axios.get(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.5',
          'Accept-Encoding': 'gzip, deflate',
          'DNT': '1',
          'Connection': 'keep-alive',
          'Upgrade-Insecure-Requests': '1'
        },
        responseType: 'arraybuffer',
        timeout: Number.isFinite(requestTimeout) ? requestTimeout : 60000
      });

      const buffer = Buffer.isBuffer(response.data)
        ? response.data
        : Buffer.from(response.data);

      const rawContentType = typeof response.headers['content-type'] === 'string'
        ? response.headers['content-type']
        : Array.isArray(response.headers['content-type'])
          ? response.headers['content-type'][0]
          : '';
      const contentType = rawContentType.toLowerCase();
      const pathLower = parsedUrl.pathname.toLowerCase();
      const looksLikePdf = contentType.includes('application/pdf') || pathLower.endsWith('.pdf');

      if (looksLikePdf) {
        const pdfArticle = await this.extractPdfArticle(buffer, url);
        if (pdfArticle) {
          return pdfArticle;
        }

        return {
          title: 'PDF Document',
          content: 'Unable to extract readable text from this PDF using built-in parsers. The document may be scanned or contain unsupported encoding.',
          url,
          author: undefined,
          publishDate: undefined
        };
      }

      const html = this.decodeBufferToString(buffer, contentType);

      // Extract title using regex
      const title = this.extractTitle(html);
      
      // Extract main content using regex
      const content = this.extractContent(html);
      
      // Extract metadata
      const author = this.extractAuthor(html);
      const publishDate = this.extractPublishDate(html);
      
      if (!content.trim()) {
        throw new Error('No content could be extracted from the URL');
      }
      
      return {
        title: title || 'Untitled Article',
        content: content.trim(),
        url,
        author,
        publishDate
      };
      
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to fetch article: ${error.message}`);
      }
      throw new Error('Failed to fetch article: Unknown error');
    }
  }

  private decodeBufferToString(buffer: Buffer, contentType: string): string {
    try {
      if (contentType.includes('charset=')) {
        const charset = contentType.split('charset=')[1]?.split(';')[0]?.trim().toLowerCase();
        if (charset && charset !== 'utf-8' && charset !== 'utf8') {
          return buffer.toString(charset as BufferEncoding);
        }
      }
    } catch (error) {
      console.warn('Character set decoding failed, falling back to UTF-8:', error);
    }
    return buffer.toString('utf-8');
  }

  private async extractPdfArticle(buffer: Buffer, url: string): Promise<ArticleContent | null> {
    try {
      const pdfData = await this.parsePdf(buffer);
      if (!pdfData) {
        return null;
      }

      const sanitizedText = this.cleanText(pdfData.text);
      if (!sanitizedText) {
        return null;
      }

      const titleFromMetadata = pdfData.info?.Title?.trim();
      const derivedTitle = titleFromMetadata || this.deriveTitleFromPdfText(sanitizedText);
      const authorFromMetadata = pdfData.info?.Author?.trim();

      return {
        title: derivedTitle || 'PDF Document',
        content: sanitizedText,
        url,
        author: authorFromMetadata,
        publishDate: undefined
      };
    } catch (error) {
      console.warn('PDF extraction failed:', error);
      return null;
    }
  }

  private async parsePdf(buffer: Buffer): Promise<{ text: string; info?: { Title?: string; Author?: string } } | null> {
    try {
      await this.ensurePdfDomPolyfills();

      const pdfParse = await this.loadPdfParse();
      if (!pdfParse) {
        return null;
      }

      const pdfResult = await pdfParse(buffer);
      if (!pdfResult?.text) {
        return null;
      }

      const normalizedText = pdfResult.text
        .replace(/\u0000/g, ' ')
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n')
        .replace(/\f/g, '\n')
        .replace(/\n{3,}/g, '\n\n')
        .trim();

      if (!normalizedText) {
        return null;
      }

      return {
        text: normalizedText,
        info: pdfResult.info
      };
    } catch (error) {
      console.warn('pdf-parse module failed:', error);
      return null;
    }
  }

  private async loadPdfParse(): Promise<((data: Uint8Array | ArrayBuffer | Buffer | string | URL | number[]) => Promise<{ text: string; info?: { Title?: string; Author?: string } | undefined }>) | null> {
    if (!URLFetcher.pdfParseLoader) {
      URLFetcher.pdfParseLoader = (async () => {
        try {
          const pdfModule = await import('pdf-parse');
          const candidates: unknown[] = [
            (pdfModule as { default?: unknown }).default,
            (pdfModule as { pdf?: unknown }).pdf,
            pdfModule
          ];

          for (const candidate of candidates) {
            if (typeof candidate === 'function') {
              return candidate as (data: Uint8Array | ArrayBuffer | Buffer | string | URL | number[]) => Promise<{ text: string; info?: { Title?: string; Author?: string } | undefined }>;
            }
          }

          console.warn('pdf-parse import did not expose a callable parser.');
        } catch (error) {
          console.warn('pdf-parse import failed:', error);
        }

        return null;
      })();
    }

    return URLFetcher.pdfParseLoader;
  }

  private async ensurePdfDomPolyfills(): Promise<void> {
    const globalAny = globalThis as Record<string, unknown>;

    if (typeof globalAny.DOMMatrix === 'undefined') {
      try {
        const domMatrixModule = await import('dommatrix');
        const DomMatrixCtor = (domMatrixModule as { default?: unknown }).default;
        if (DomMatrixCtor && typeof DomMatrixCtor === 'function') {
          globalAny.DOMMatrix = DomMatrixCtor;
        }
      } catch (error) {
        console.warn('DOMMatrix polyfill unavailable:', error);
      }
    }

    if (typeof globalAny.Path2D === 'undefined') {
      class Path2DShim {
        constructor(_path?: string | Path2D) {
          // Path arguments ignored in server environment
          void _path;
        }
        addPath(): void {
          // No drawing support needed on server
          void 0;
        }
      }
      globalAny.Path2D = Path2DShim;
    }

    if (typeof globalAny.ImageData === 'undefined') {
      class ImageDataShim {
        data: Uint8ClampedArray;
        width: number;
        height: number;
        constructor(data: Uint8ClampedArray, width: number, height: number) {
          this.data = data;
          this.width = width;
          this.height = height;
        }
      }
      globalAny.ImageData = ImageDataShim;
    }
  }

  private deriveTitleFromPdfText(text: string): string {
    const lines = text.split('\n').map(line => line.trim()).filter(Boolean);
    for (const line of lines) {
      if (line.length >= 8 && line.length <= 180) {
        return line.replace(/\s+/g, ' ');
      }
    }
    return 'PDF Document';
  }

  private extractTitle(html: string): string {
    // Try to extract title from various meta tags and h1
    const patterns = [
      /<title[^>]*>([^<]+)<\/title>/i,
      /<meta[^>]*property="og:title"[^>]*content="([^"]*)"[^>]*>/i,
      /<meta[^>]*name="twitter:title"[^>]*content="([^"]*)"[^>]*>/i,
      /<h1[^>]*>([^<]+)<\/h1>/i
    ];

    for (const pattern of patterns) {
      const match = html.match(pattern);
      if (match && match[1] && match[1].trim()) {
        return this.cleanText(match[1]);
      }
    }

    return '';
  }

  private extractContent(html: string): string {
    // Remove script and style tags
    let cleanHtml = html.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
    cleanHtml = cleanHtml.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
    
    // Priority 1: Extract from main tag (for documentation sites)
    const mainMatch = cleanHtml.match(/<main[^>]*>([\s\S]*?)<\/main>/i);
    if (mainMatch) {
      const mainContent = this.extractTextFromHtml(mainMatch[1]);
      if (mainContent.length > 200) {
        return mainContent;
      }
    }

    // Priority 2: Try to extract content from article tags
    const articleMatch = cleanHtml.match(/<article[^>]*>([\s\S]*?)<\/article>/i);
    if (articleMatch) {
      const articleContent = this.extractTextFromHtml(articleMatch[1]);
      if (articleContent.length > 100) {
        return articleContent;
      }
    }

    // Priority 3: Try to extract from common documentation content areas
    const docContentPatterns = [
      /<div[^>]*class="[^"]*content[^"]*"[^>]*>([\s\S]*?)<\/div>/i,
      /<div[^>]*class="[^"]*article[^"]*"[^>]*>([\s\S]*?)<\/div>/i,
      /<div[^>]*class="[^"]*post[^"]*"[^>]*>([\s\S]*?)<\/div>/i,
      /<div[^>]*class="[^"]*documentation[^"]*"[^>]*>([\s\S]*?)<\/div>/i,
      /<section[^>]*class="[^"]*content[^"]*"[^>]*>([\s\S]*?)<\/section>/i
    ];

    for (const pattern of docContentPatterns) {
      const match = cleanHtml.match(pattern);
      if (match && match[1]) {
        const text = this.extractTextFromHtml(match[1]);
        if (text.length > 100) {
          return text;
        }
      }
    }

    // Priority 4: Extract all meaningful div content (for modern SPA docs)
    const allDivs = cleanHtml.match(/<div[^>]*>[\s\S]*?<\/div>/gi);
    if (allDivs) {
      const meaningfulContent = allDivs
        .map(div => this.extractTextFromHtml(div))
        .filter(text => text.length > 50) // Filter out short/meaningless divs
        .join('\n\n');
      
      if (meaningfulContent.length > 200) {
        return meaningfulContent;
      }
    }

    // Priority 5: Fallback to paragraph content
    const paragraphs = cleanHtml.match(/<p[^>]*>([^<]*(?:<[^\/p>]*>[^<]*<\/[^>]*>[^<]*)*)<\/p>/gi);
    if (paragraphs) {
      const content = paragraphs
        .map(p => this.extractTextFromHtml(p))
        .filter(text => text.length > 20)
        .join('\n\n');
      
      if (content.trim()) {
        return content;
      }
    }

    // Last resort: extract text from body
    const bodyMatch = cleanHtml.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    if (bodyMatch) {
      return this.extractTextFromHtml(bodyMatch[1]);
    }

    return this.extractTextFromHtml(cleanHtml);
  }

  private extractAuthor(html: string): string | undefined {
    const patterns = [
      /<meta[^>]*name="author"[^>]*content="([^"]*)"[^>]*>/i,
      /<meta[^>]*property="article:author"[^>]*content="([^"]*)"[^>]*>/i,
      /<span[^>]*class="[^"]*author[^"]*"[^>]*>([^<]+)<\/span>/i
    ];

    for (const pattern of patterns) {
      const match = html.match(pattern);
      if (match && match[1] && match[1].trim()) {
        return this.cleanText(match[1]);
      }
    }

    return undefined;
  }

  private extractPublishDate(html: string): string | undefined {
    const patterns = [
      /<meta[^>]*property="article:published_time"[^>]*content="([^"]*)"[^>]*>/i,
      /<meta[^>]*name="date"[^>]*content="([^"]*)"[^>]*>/i,
      /<time[^>]*datetime="([^"]*)"[^>]*>/i
    ];

    for (const pattern of patterns) {
      const match = html.match(pattern);
      if (match && match[1] && match[1].trim()) {
        return match[1].trim();
      }
    }

    return undefined;
  }

  private extractTextFromHtml(html: string): string {
    // First, handle block elements to preserve structure
    let text = html
      // Convert block elements to newlines
      .replace(/<\/?(div|p|h[1-6]|section|article|header|footer|nav|main|aside)[^>]*>/gi, '\n')
      // Convert list items to bullet points
      .replace(/<li[^>]*>/gi, '\n• ')
      .replace(/<\/li>/gi, '')
      // Convert breaks to newlines
      .replace(/<br[^>]*>/gi, '\n')
      // Remove all other HTML tags
      .replace(/<[^>]*>/g, ' ');
    
    // Decode common HTML entities
    text = text
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .replace(/&nbsp;/g, ' ')
      .replace(/&hellip;/g, '...')
      .replace(/&mdash;/g, '—')
      .replace(/&ndash;/g, '–')
      .replace(/&rsquo;/g, "'")
      .replace(/&lsquo;/g, "'")
      .replace(/&rdquo;/g, '"')
      .replace(/&ldquo;/g, '"');
    
    return this.cleanText(text);
  }

  private cleanText(text: string): string {
    return text
      // Normalize whitespace while preserving line breaks
      .replace(/[ \t]+/g, ' ') // Replace multiple spaces/tabs with single space
      .replace(/\n[ \t]+/g, '\n') // Remove leading spaces from new lines
      .replace(/[ \t]+\n/g, '\n') // Remove trailing spaces from lines
      .replace(/\n{3,}/g, '\n\n') // Replace multiple newlines with double newlines
      .replace(/^\n+/, '') // Remove leading newlines
      .replace(/\n+$/, '') // Remove trailing newlines
      .trim();
  }
}
