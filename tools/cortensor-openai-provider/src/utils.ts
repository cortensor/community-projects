import type { CoreMessage } from "ai";
import type { OpenAIResponse, WebSearchResult } from "./types";
import { SEARCH_SNIPPET_WORD_LIMIT } from "./constants";

/**
 * Creates a standardized error response in OpenAI format
 * @param errorMessage - The error message to include
 * @returns OpenAI-formatted error response
 */
export function createErrorResponse(errorMessage: string = 'Sorry, I encountered an error processing your request.'): OpenAIResponse {
    return {
        id: `cortensor-error-${Date.now()}`,
        object: 'chat.completion',
        created: Math.floor(Date.now() / 1000),
        model: 'cortensor-model',
        choices: [
            {
                index: 0,
                message: {
                    role: 'assistant' as const,
                    content: errorMessage
                },
                finish_reason: 'stop'
            }
        ]
    };
}
  


/**
 * Builds a formatted prompt from system and conversation messages
 * @param systemMessages - Array of system messages
 * @param conversationMessages - Array of conversation messages
 * @returns Formatted prompt string
 */
export function buildFormattedPrompt(systemMessages: CoreMessage[], conversationMessages: CoreMessage[]): string {
    let prompt = '';

    // Add system instructions section if present
    if (systemMessages.length > 0) {
        const systemInstructions = systemMessages
            .map((msg, index) => {
                const content = extractMessageContent(msg);
                return content;
            })
            .join('\n\n');

        prompt += `### SYSTEM INSTRUCTIONS ###\n${systemInstructions}\n\n### CONVERSATION ###\n`;
    }

    // Add conversation history with role formatting
    const conversationText = conversationMessages
        .map((msg, index) => {
            const content = extractMessageContent(msg);
            switch (msg.role) {
                case 'user':
                    return `Human: ${content}`;
                case 'assistant':
                    return `Assistant: ${content}`;
                default:
                    return content;
            }
        })
        .join('\n\n');

    prompt += conversationText;

    // Get current date and time for context
    const now = new Date();
    const currentDateTime = now.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }) + ' at ' + now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZoneName: 'short'
    });

    prompt += `\n\n--- CURRENT DATE AND TIME ---\n${currentDateTime}`;

    // Add assistant prompt if the last message is from user
    const lastMessage = conversationMessages[conversationMessages.length - 1];
    if (conversationMessages.length > 0 && lastMessage?.role === 'user') {
        prompt += '\n\nAssistant:';
    }
    
    return prompt;
}
  

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Extracts text content from a message, handling both string and array formats
 * @param message - The message to extract content from
 * @returns The extracted text content
 */
export function extractMessageContent(message: CoreMessage): string {
    if (typeof message.content === 'string') {
        return message.content;
    }

    if (Array.isArray(message.content)) {
        const extractedContent = message.content
            .filter(part => {
                // Handle string parts
                if (typeof part === 'string') {
                    return true;
                }
                // Handle text objects
                if (typeof part === 'object' && part !== null && 'type' in part) {
                    return part.type === 'text';
                }
                return false;
            })
            .map(part => {
                if (typeof part === 'string') {
                    return part;
                }
                // Extract text from text objects
                const text = (part as any).text || '';
                return text;
            })
            .join(' ')
            .trim();
        return extractedContent;
    }

    return '';
}
  

/**
 * Formats search results as numbered citations with a sources section
 * @param results - Array of search results
 * @returns Formatted search results with numbered citations and sources section
 */
export function formatSearchResults(
    results: WebSearchResult[]
): string {
    if (results.length === 0) {
        return '';
    }

    // Create the sources section
    const sources = results
        .map((result, index) => {
            return `[${index + 1}] [${result.title}](${result.url})`;
        })
        .join('\n');

    const formattedResults = `\n\n**Sources:**\n${sources}`;

    return formattedResults;
}

/**
 * Truncates a snippet to the specified number of words
 * @param snippet - The snippet text to truncate
 * @param wordLimit - Maximum number of words to include (defaults to SEARCH_SNIPPET_WORD_LIMIT)
 * @returns Truncated snippet with ellipsis if truncated
 */
export function truncateSnippet(snippet: string, wordLimit: number = SEARCH_SNIPPET_WORD_LIMIT): string {
    if (!snippet || snippet.trim().length === 0) {
        return '';
    }

    const words = snippet.trim().split(/\s+/);
    
    if (words.length <= wordLimit) {
        return snippet.trim();
    }
    
    const truncated = words.slice(0, wordLimit).join(' ');
    return `${truncated}...`;
}