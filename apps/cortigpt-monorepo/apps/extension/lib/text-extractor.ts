/**
 * Simple text extraction utilities
 * Manages single current selection with automatic cleanup
 */

import { extractSelectedText, TextSelection, SelectionOptions, hasSelection } from './selection-utils';
import { 
  setCurrentSelection, 
  clearCurrentSelection, 
  hasCurrentSelection, 
  getCurrentText, 
  hasTextChanged, 
  getSelectionStats, 
  clearAll,
  getCurrentSelection,
  SelectionStats, 
  CurrentSelection 
} from './selection-storage';

// Re-export types for backward compatibility
export interface TextExtractionResult extends TextSelection {}
export interface TextExtractionOptions extends SelectionOptions {}

/**
 * Extract and track current text selection
 * Automatically clears previous selection and handles unhighlighting
 */
export function extractAndTrackSelection(options: TextExtractionOptions = {}): TextExtractionResult | null {
  const selection = extractSelectedText(options);
  
  // If no selection exists, clear current selection (unhighlight detected)
  if (!selection || !selection.text.trim()) {
    if (hasCurrentSelection()) {
      clearCurrentSelection();
      console.log('[TextExtractor] Selection cleared (unhighlighted)');
    }
    return null;
  }

  // Set new selection (replaces any previous selection)
  setCurrentSelection(selection.text);
  console.log('[TextExtractor] New selection stored:', selection.text.substring(0, 50) + '...');

  return selection;
}

/**
 * Get the current selected text
 */
export function getCurrentSelectedText(): string {
  return getCurrentText();
}

/**
 * Check if there is currently a selection
 */
export function hasCurrentTextSelection(): boolean {
  return hasCurrentSelection();
}

/**
 * Get statistics about the current selection
 */
export function getCurrentSelectionStats(): SelectionStats {
  return getSelectionStats();
}

/**
 * Clear the current selection
 */
export function clearCurrentTextSelection(): void {
  clearAll();
}

/**
 * Get the current selection object
 */
export function getCurrentSelectionData(): CurrentSelection | null {
  return getCurrentSelection();
}

// Legacy compatibility object
export const textExtractor = {
  extractSelectedText: extractAndTrackSelection,
  getCurrentText: getCurrentSelectedText,
  hasSelection: hasCurrentTextSelection,
  getSelectionStats: getCurrentSelectionStats,
  clearSelection: clearCurrentTextSelection,
  getCurrentSelection: getCurrentSelectionData
};