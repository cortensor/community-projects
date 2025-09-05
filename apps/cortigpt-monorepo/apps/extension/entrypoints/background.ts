import { defineBackground } from '#imports';
import type {
  ExtensionMessage,
  TextSelectionData,
  MessageResponse,
  TextSelectedMessage,
  GetSelectedTextMessage,
  ClearSelectedTextMessage
} from '../types/messaging';

// Simple background script for text selection management
export default defineBackground(() => {
  console.log('[Background] Background script loaded');

  // Global state for selected text
  let currentSelection: TextSelectionData | null = null;

  /**
   * Store current text selection
   */
  function storeTextSelection(textData: TextSelectionData): void {
    currentSelection = textData;
    console.log('[Background] Text selection stored:', textData.text.substring(0, 50) + '...');
  }

  /**
   * Notify sidepanel about text selection update
   */
  async function notifySidepanel(textData: TextSelectionData): Promise<void> {
    try {
      const tabs = await browser.tabs.query({ active: true, currentWindow: true });
      if (tabs[0]?.id) {
        await browser.runtime.sendMessage({
          type: 'TEXT_SELECTION_UPDATE',
          data: textData
        });
      }
    } catch (error) {
      console.log('[Background] Could not notify sidepanel:', error);
    }
  }





  // Handle tab changes to clear selected text
  browser.tabs.onActivated.addListener(async (activeInfo) => {
    try {
      // Clear current selection when tab changes
      if (currentSelection) {
        console.log('[Background] Tab changed, clearing selected text');
        currentSelection = null;
        
        // Notify sidepanel to clear the preview
        await browser.runtime.sendMessage({
          type: 'TEXT_SELECTION_UPDATE',
          data: null
        });
      }
    } catch (error) {
      console.log('[Background] Failed to handle tab change:', error);
    }
  });

  // Handle tab updates (URL changes within same tab)
  browser.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
    try {
      // Clear selection when URL changes (navigation within tab)
      if (changeInfo.url && currentSelection) {
        console.log('[Background] Page navigation detected, clearing selected text');
        currentSelection = null;
        
        // Notify sidepanel to clear the preview
        await browser.runtime.sendMessage({
          type: 'TEXT_SELECTION_UPDATE',
          data: null
        });
      }
    } catch (error) {
      console.log('[Background] Failed to handle tab update:', error);
    }
  });

  // Handle extension icon click to open sidepanel
  browser.action.onClicked.addListener(async (tab) => {
    try {
      if (tab.id) {
        await browser.sidePanel.open({ tabId: tab.id });
      }
    } catch (error) {
      console.error('[Background] Failed to open sidepanel:', error);
    }
  });

  // Set up sidepanel options on install
  browser.runtime.onInstalled.addListener(async () => {
    try {
      await browser.sidePanel.setOptions({
        path: 'sidepanel.html',
        enabled: true
      });

      await browser.sidePanel.setPanelBehavior({
        openPanelOnActionClick: true
      });
    } catch (error) {
      console.error('[Background] Failed to configure sidepanel:', error);
    }
  });

  // Handle messages from content script and sidepanel
  browser.runtime.onMessage.addListener(
    async (message: ExtensionMessage, sender: Browser.runtime.MessageSender, sendResponse: (response: MessageResponse) => void) => {
      try {
        if (message.type === 'TEXT_SELECTED') {
          const textMessage = message as TextSelectedMessage;

          // Validate message data
          if (!textMessage.text || !textMessage.url) {
            sendResponse({ success: false });
            return;
          }

          // Store the selected text from content script
          const textData: TextSelectionData = {
            text: textMessage.text,
            url: textMessage.url,
            timestamp: textMessage.timestamp
          };

          storeTextSelection(textData);

          // Notify sidepanel asynchronously
          await notifySidepanel(textData);

          sendResponse({ success: true });
        }

        else if (message.type === 'GET_SELECTED_TEXT') {
          sendResponse({
            success: true,
            data: currentSelection
          });
        }

        else if (message.type === 'CLEAR_SELECTED_TEXT') {
          currentSelection = null;
          sendResponse({ success: true });
        }



        else {
          sendResponse({ success: false });
        }

      } catch (error) {
        console.error('[Background] Message processing failed:', error);
        sendResponse({ success: false });
      }

      return true; // Keep the message channel open for async response
    }
  );

  console.log('[Background] Background script initialized');
});
