/**
 * Core text selection utilities
 * Simple, focused functions for extracting text from DOM selections
 */

export interface TextSelection {
  text: string;
  range?: Range;
  boundingRect?: DOMRect;
  elementContext?: {
    tagName: string;
    className: string;
    id: string;
  };
}

export interface SelectionOptions {
  minLength?: number;
  maxLength?: number;
  trimWhitespace?: boolean;
  includeContext?: boolean;
}

/**
 * Get the current text selection from the DOM
 * Returns null if no valid selection exists
 */
export function getCurrentSelection(): Selection | null {
  return window.getSelection();
}

/**
 * Extract text from the current selection
 * Applies basic validation and formatting
 */
export function extractSelectedText(options: SelectionOptions = {}): TextSelection | null {
  const selection = getCurrentSelection();
  
  if (!selection || selection.rangeCount === 0) {
    return null;
  }

  const range = selection.getRangeAt(0);
  let text = selection.toString();

  // Apply text processing options
  if (options.trimWhitespace !== false) {
    text = text.trim();
  }

  if (!text) {
    return null;
  }

  // Validate text length
  if (options.minLength && text.length < options.minLength) {
    return null;
  }

  if (options.maxLength && text.length > options.maxLength) {
    text = text.substring(0, options.maxLength);
  }

  const result: TextSelection = {
    text,
    range: range.cloneRange()
  };

  // Add bounding rectangle if available
  try {
    result.boundingRect = range.getBoundingClientRect();
  } catch (error) {
    console.warn('Failed to get selection bounds:', error);
  }

  // Add element context if requested
  if (options.includeContext) {
    result.elementContext = getElementContext(range);
  }

  return result;
}

/**
 * Get context information about the element containing the selection
 */
export function getElementContext(range: Range): { tagName: string; className: string; id: string } | undefined {
  try {
    const container = range.commonAncestorContainer;
    const element = container.nodeType === Node.ELEMENT_NODE 
      ? container as Element 
      : container.parentElement;
    
    if (element) {
      return {
        tagName: element.tagName.toLowerCase(),
        className: element.className || '',
        id: element.id || ''
      };
    }
  } catch (error) {
    console.warn('Failed to get element context:', error);
  }
  
  return undefined;
}

/**
 * Check if there is currently any text selected
 */
export function hasSelection(): boolean {
  const selection = getCurrentSelection();
  return !!(selection && selection.rangeCount > 0 && selection.toString().trim());
}

/**
 * Clear the current selection
 */
export function clearSelection(): void {
  const selection = getCurrentSelection();
  if (selection) {
    selection.removeAllRanges();
  }
}

/**
 * Get the selected text as plain string
 * Returns empty string if no selection
 */
export function getSelectedText(): string {
  const selection = getCurrentSelection();
  return selection ? selection.toString().trim() : '';
}