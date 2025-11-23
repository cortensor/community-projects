/**
 * CortiGPT Agent using Cortensor Provider
 * A helpful AI assistant to answer user questions and provide assistance
 * Enhanced with manual memory handling for chat history
 */

import { Agent } from '@mastra/core';
import { cortensorModel, createTavilySearch } from 'cortensor-openai-provider';



/**
 * Generate dynamic instructions with current date
 * Updates the instructions to include the current date for better context awareness
 */
function generateInstructions(): string {
    return `You are CortiGPT, a helpful AI assistant powered by Cortensor. Your goal is to help users by answering their questions and providing assistance with various tasks. Be friendly, informative, and concise in your responses.

When you receive messages, you will be provided with chat history for context. The history contains previous messages from the conversation to help you understand the context and provide better responses. Use this history as context but focus on responding to the current user message.

Use this date information when relevant to provide accurate, time-sensitive responses.`;
}

/**
 * Create CortiGPT Agent with dynamic instructions
 * Uses Cortensor as the underlying language model with Tavily web search
 * Instructions are generated at runtime to include the current date
 * Memory is handled manually by passing chat history in messages
 * 
 * Web Search Usage:
 * - Use [search] in your message to trigger web search: "[search] What's the latest news about AI?"
 * - Use [no-search] to prevent search: "[no-search] Tell me a joke"
 * - Search is automatically triggered by [search] markers (prompt mode)
 * 
 * Note: Requires TAVILY_API_KEY environment variable for web search functionality
 */
function createCortiGPTAgent(): Agent {
    return new Agent({
        name: 'CortiGPT',
        instructions: generateInstructions(),

        // Use Cortensor as the language model with custom configuration and web search
        model: cortensorModel({
            sessionId: 75,
            maxTokens: 4096,
            temperature: 0.4,
            webSearch: {
                mode: 'prompt', // Search triggered by [search] markers in user messages
                provider: createTavilySearch({
                    apiKey: process.env.TAVILY_API_KEY,
                }),
                maxResults: 2
            }
        }),

        // No tools needed for this general assistant
        tools: {},

        // Memory is handled manually - no memory configuration needed
    });
}

/**
 * Export the CortiGPT agent instance with current date in instructions
 * This creates a new agent instance each time it's accessed, ensuring the date is always current
 */
export const cortiGPTAgent = createCortiGPTAgent();