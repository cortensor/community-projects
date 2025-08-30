// Message types for communication between content script, background, and sidepanel

export interface TextSelectionData {
  text: string;
  url: string;
  timestamp: number;
}

export interface TextSelectedMessage {
  type: 'TEXT_SELECTED';
  text: string;
  url: string;
  timestamp: number;
}

export interface TextSelectionUpdateMessage {
  type: 'TEXT_SELECTION_UPDATE';
  data: TextSelectionData | null;
}

export interface GetSelectedTextMessage {
  type: 'GET_SELECTED_TEXT';
}

export interface ClearSelectedTextMessage {
  type: 'CLEAR_SELECTED_TEXT';
}



export interface MessageResponse {
  success: boolean;
  data?: TextSelectionData | null;
}

export type ExtensionMessage =
  | TextSelectedMessage
  | TextSelectionUpdateMessage
  | GetSelectedTextMessage
  | ClearSelectedTextMessage;

export interface SelectedTextPreview {
  originalText: string;
  truncatedText: string;
  url: string;
  timestamp: number;
  isVisible: boolean;
}