/**
 * Core messaging utilities for extension communication
 * Simple, focused functions for sending messages between extension components
 */

import type {
  ExtensionMessage,
  TextSelectedMessage,
  MessageResponse
} from '../types/messaging';

// Declare chrome types for compatibility
declare global {
  const chrome: typeof browser;
}

export interface SendOptions {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
}

export interface MessageStats {
  sent: number;
  failed: number;
  lastActivity: number;
}

// Internal state
let messageStats: MessageStats = {
  sent: 0,
  failed: 0,
  lastActivity: Date.now()
};

/**
 * Send a text selection message to the background script
 * Simple wrapper for the most common messaging use case
 */
export async function sendTextSelection(
  text: string,
  url: string = window.location.href,
  options: SendOptions = {}
): Promise<MessageResponse> {
  const message: TextSelectedMessage = {
    type: 'TEXT_SELECTED',
    text,
    url,
    timestamp: Date.now()
  };

  console.log('[Messaging] Sending text selection:', text.substring(0, 50) + '...');
  return sendMessage(message, options);
}

/**
 * Send any extension message with basic retry logic
 * Core messaging function with minimal complexity
 */
export async function sendMessage(
  message: ExtensionMessage,
  options: SendOptions = {}
): Promise<MessageResponse> {
  const defaultOptions: SendOptions = {
    timeout: 5000,
    retries: 3,
    retryDelay: 1000,
    ...options
  };

  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= (defaultOptions.retries || 3); attempt++) {
    try {
      const response = await sendSingleMessage(message, defaultOptions.timeout || 5000);

      messageStats.sent++;
      messageStats.lastActivity = Date.now();

      if (attempt > 1) {
        console.log(`[Messaging] Success on attempt ${attempt}`);
      }

      return response;

    } catch (error) {
      lastError = error as Error;
      messageStats.failed++;

      if (attempt < (defaultOptions.retries || 3)) {
        console.warn(`[Messaging] Attempt ${attempt} failed, retrying...`);
        await delay(defaultOptions.retryDelay || 1000);
      }
    }
  }

  console.error('[Messaging] All attempts failed:', lastError?.message);
  throw lastError || new Error('Message send failed after all retries');
}

/**
 * Send a single message with timeout
 * Low-level messaging function
 */
export async function sendSingleMessage(
  message: ExtensionMessage,
  timeout: number = 5000
): Promise<MessageResponse> {
  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error(`Message timeout after ${timeout}ms`));
    }, timeout);

    try {
      if (typeof browser !== 'undefined' && browser?.runtime?.sendMessage) {
        browser.runtime.sendMessage(message)
          .then((response: MessageResponse) => {
            clearTimeout(timeoutId);
            if (response && response.success) {
              resolve(response);
            } else {
              reject(new Error('Message response indicates failure'));
            }
          })
          .catch((error: any) => {
            clearTimeout(timeoutId);
            reject(error);
          });
      } else if (typeof chrome !== 'undefined' && chrome?.runtime?.sendMessage) {
        chrome.runtime.sendMessage(message)
          .then((response: MessageResponse) => {
            clearTimeout(timeoutId);
            if (response && response.success) {
              resolve(response);
            } else {
              reject(new Error('Message response indicates failure'));
            }
          })
          .catch((error: any) => {
            clearTimeout(timeoutId);
            reject(error);
          });
      } else {
        clearTimeout(timeoutId);
        reject(new Error('Browser runtime not available'));
      }
    } catch (error) {
      clearTimeout(timeoutId);
      reject(error);
    }
  });
}

/**
 * Get current messaging statistics
 */
export function getMessageStats(): MessageStats {
  return { ...messageStats };
}

/**
 * Reset messaging statistics
 */
export function resetMessageStats(): void {
  messageStats = {
    sent: 0,
    failed: 0,
    lastActivity: Date.now()
  };
  console.log('[Messaging] Stats reset');
}

/**
 * Check if messaging is working (has recent activity)
 */
export function isMessagingHealthy(): boolean {
  const timeSinceLastActivity = Date.now() - messageStats.lastActivity;
  return timeSinceLastActivity < 60000; // 1 minute threshold
}

/**
 * Setup message listener for extension messages
 * Handles incoming messages from other parts of the extension
 */
export function setupMessageListener(
  handler: (message: any, sender: any, sendResponse: (response: any) => void) => void
): void {
  try {
    if (typeof browser !== 'undefined' && browser?.runtime?.onMessage) {
      browser.runtime.onMessage.addListener((message: any, sender: any, sendResponse: any) => {
        messageStats.lastActivity = Date.now();
        handler(message, sender, sendResponse);
        return true; // Keep message channel open for async responses
      });
      console.log('[Messaging] Listener setup complete');
    } else if (typeof chrome !== 'undefined' && chrome?.runtime?.onMessage) {
      chrome.runtime.onMessage.addListener((message: any, sender: any, sendResponse: any) => {
        messageStats.lastActivity = Date.now();
        handler(message, sender, sendResponse);
        return true; // Keep message channel open for async responses
      });
      console.log('[Messaging] Listener setup complete');
    } else {
      console.warn('[Messaging] Browser runtime not available for message listener');
    }
  } catch (error) {
    console.warn('[Messaging] Error setting up message listener:', error);
  }
}

/**
 * Simple delay utility
 */
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}