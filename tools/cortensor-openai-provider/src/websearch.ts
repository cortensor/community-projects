import type { CoreMessage } from "ai";
import { WebSearchError } from "./provider";
import type { CortensorModelConfig, WebSearchCallback, WebSearchResult } from "./types";
import { extractMessageContent, truncateSnippet } from "./utils";

/**
 * Simple web search function
 */
async function performWebSearch(
    query: string,
    provider: WebSearchCallback,
    maxResults: number
): Promise<WebSearchResult[]> {
    try {
        if (typeof provider === 'function') {
            return await provider(query, maxResults);
        } else {
            return await provider.search(query, maxResults);
        }
    } catch (error) {
        throw new WebSearchError(`Web search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
}

/**
 * Simple web search handler
 */
export async function handleWebSearch(
    messages: CoreMessage[],
    webSearchConfig?: CortensorModelConfig['webSearch']
): Promise<{ query: string; results: WebSearchResult[] } | null> {
    if (!webSearchConfig?.provider) {
        return null;
    }

    const searchQuery = generateSearchQuery(messages);

    if (!searchQuery) {
        return null;
    }

    try {
        const searchResults = await performWebSearch(searchQuery, webSearchConfig.provider, webSearchConfig.maxResults || 5);

        const result = { query: searchQuery, results: searchResults };
        return result;
    } catch (error) {
        return null;
    }
}



/**
 * Builds a prompt enhanced with search results
 */
export function buildPromptWithSearchResults(
    messages: CoreMessage[],
    searchResults: WebSearchResult[],
    searchQuery: string
): string {

    // Build basic prompt
    let prompt = '';
    const systemMessages = messages.filter(msg => msg.role === 'system');
    const conversationMessages = messages.filter(msg => msg.role !== 'system');
    
    if (systemMessages.length > 0) {
        prompt += systemMessages.map(msg => extractMessageContent(msg)).join('\n\n') + '\n\n';
    }
    
    conversationMessages.forEach(msg => {
        const content = extractMessageContent(msg);
        if (msg.role === 'user') {
            prompt += `Human: ${content}\n\n`;
        } else {
            prompt += `Assistant: ${content}\n\n`;
        }
    });



    // Add current date/time
    const now = new Date();
    const currentDateTime = now.toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    }) + ' at ' + now.toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
    });

    // Add search results (with truncated snippets, no URLs in prompt)
    const searchContent = searchResults.length > 0 
        ? searchResults.map((result, index) => {
            const truncatedSnippet = result.snippet ? truncateSnippet(result.snippet) : 'No content available';
            return `${result.title}: ${truncatedSnippet}`;
        }).join('\n\n')
        : 'No search results found.';
    
    const finalPrompt = `${prompt}Current date and time: ${currentDateTime}\n\nSearch results for "${searchQuery}":\n\n${searchContent}\n\nAssistant:`;

    return finalPrompt;
}



/**
 * Simple search query generator - uses first 390 chars of latest message
 */
export function generateSearchQuery(messages: CoreMessage[]): string {
    if (messages.length === 0) {
        return 'general information';
    }

    const lastMessage = messages[messages.length - 1];
    if (!lastMessage) {
        return 'general information';
    }

    const content = extractMessageContent(lastMessage);

    // Take first 390 characters
    const searchQuery = content.substring(0, 390).trim();

    return searchQuery;
}


/**
 * Simple search directive checker - checks for [**search**] marker
 */
export function extractSearchDirectives(
    messages: CoreMessage[],
    webSearchConfig?: CortensorModelConfig['webSearch']
): { shouldSearch: boolean; cleanedMessages: CoreMessage[] } {
    if (!webSearchConfig || messages.length === 0) {
        return { shouldSearch: false, cleanedMessages: messages };
    }

    const lastMessage = messages[messages.length - 1];
    if (!lastMessage) {
        return { shouldSearch: false, cleanedMessages: messages };
    }

    const content = extractMessageContent(lastMessage);

    // Check for search markers
    const hasSearchMarker = /\[\*\*search\*\*\]/i.test(content);
    const hasNoSearchMarker = /\[\*\*no-search\*\*\]/i.test(content);

    // Determine if search should be performed
    let shouldSearch = false;
    if (webSearchConfig.mode === 'force') {
        shouldSearch = true;
    } else if (webSearchConfig.mode === 'disable') {
        shouldSearch = false;
    } else { // prompt-based mode
        shouldSearch = hasSearchMarker && !hasNoSearchMarker;
    }

    // Clean the content by removing markers
    const cleanedContent = content.replace(/\[\*\*search\*\*\]/gi, '').replace(/\[\*\*no-search\*\*\]/gi, '').trim();

    const cleanedMessages: CoreMessage[] = [
        ...messages.slice(0, -1),
        { ...lastMessage, content: cleanedContent as any }
    ];

    return { shouldSearch, cleanedMessages };
}

