/**
 * Simplified message handling utilities
 * Combines messaging functions with minimal logging and complexity
 */

import { sendTextSelection, sendMessage, getMessageStats, resetMessageStats, isMessagingHealthy, setupMessageListener } from './messaging-utils';
import type { MessageResponse } from '../types/messaging';

// Re-export types for backward compatibility
export interface MessageOptions {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
}

export interface MessageStats {
  sent: number;
  failed: number;
  lastActivity: number;
}

/**
 * Send a text selection message
 * Main function for sending selected text to background script
 */
export async function sendTextSelectionMessage(
  text: string, 
  url: string = window.location.href,
  options: MessageOptions = {}
): Promise<MessageResponse> {
  return sendTextSelection(text, url, options);
}

/**
 * Send any extension message
 * General purpose messaging function
 */
export async function sendExtensionMessage(
  message: any, 
  options: MessageOptions = {}
): Promise<MessageResponse> {
  return sendMessage(message, options);
}

/**
 * Get messaging statistics
 */
export function getMessagingStats(): MessageStats {
  return getMessageStats();
}

/**
 * Reset messaging statistics
 */
export function resetMessagingStats(): void {
  resetMessageStats();
}

/**
 * Check if messaging is healthy
 */
export function isMessagingActive(): boolean {
  return isMessagingHealthy();
}

/**
 * Initialize message listener
 */
export function initializeMessageListener(): void {
  setupMessageListener((message, sender, sendResponse) => {
    console.log('[MessageHandler] Received message:', message);
    // Handle incoming messages here
    sendResponse({ success: true });
  });
  console.log('[MessageHandler] Initialized');
}

// Legacy compatibility - simple object with main functions
export const messageHandler = {
  sendTextSelection: sendTextSelectionMessage,
  sendMessage: sendExtensionMessage,
  getStats: getMessagingStats,
  resetStats: resetMessagingStats,
  isHealthy: isMessagingActive
};

// Initialize listener on import
initializeMessageListener();