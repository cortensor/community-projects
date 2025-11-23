/**
 * Simple current selection storage utilities
 * Manages only the currently highlighted text with automatic cleanup
 */

import { MAX_TEXT_LENGTH } from './constants';

export interface CurrentSelection {
  text: string;
  timestamp: number;
  url: string;
}

export interface SelectionStats {
  hasSelection: boolean;
  textLength: number;
  timestamp?: number;
}

// Internal state - only stores current selection
let currentSelection: CurrentSelection | null = null;

// Removed local constant - now using imported value from constants.ts

/**
 * Set the current text selection
 * Replaces any previous selection and truncates if too long
 */
export function setCurrentSelection(text: string, url?: string): void {
  // Truncate text if it exceeds the maximum length
  const truncatedText = text.length > MAX_TEXT_LENGTH 
    ? text.substring(0, MAX_TEXT_LENGTH) + '...'
    : text;

  currentSelection = {
    text: truncatedText,
    timestamp: Date.now(),
    url: url || window.location.href
  };
}

/**
 * Get the current selection
 */
export function getCurrentSelection(): CurrentSelection | null {
  return currentSelection;
}

/**
 * Clear the current selection (called when text is unhighlighted)
 */
export function clearCurrentSelection(): void {
  currentSelection = null;
}

/**
 * Check if there is a current selection
 */
export function hasCurrentSelection(): boolean {
  return currentSelection !== null;
}

/**
 * Get the current selected text (empty string if none)
 */
export function getCurrentText(): string {
  return currentSelection?.text || '';
}

/**
 * Check if the provided text is different from the current selection
 */
export function hasTextChanged(text: string): boolean {
  const currentText = getCurrentText();
  return text !== currentText;
}

/**
 * Get statistics about the current selection
 */
export function getSelectionStats(): SelectionStats {
  return {
    hasSelection: hasCurrentSelection(),
    textLength: getCurrentText().length,
    timestamp: currentSelection?.timestamp
  };
}

/**
 * Clear all selection data
 */
export function clearAll(): void {
  clearCurrentSelection();
}