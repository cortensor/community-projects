import { extractAndTrackSelection } from '../lib/text-extractor';
import { sendTextSelectionMessage } from '../lib/message-handler';

export default defineContentScript({
  matches: ['<all_urls>'],
  main() {
    console.log('[ContentScript] Cortensor content script loaded', {
      url: window.location.href,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent.substring(0, 100)
    });



    /**
     * Handle text selection with simplified logging
     */
    async function handleTextSelection(): Promise<void> {
      try {
        const result = extractAndTrackSelection();

        if (result && result.text) {
          console.log('[Content] Text selected:', result.text.substring(0, 50) + '...');

          try {
            await sendTextSelectionMessage(result.text);
            console.log('[Content] Text sent successfully');
          } catch (error) {
            console.error('[Content] Failed to send text:', error);
          }
        }
      } catch (error) {
        console.error('[Content] Selection error:', error);
      }
    }



    /**
      * Debounced text selection handler with unhighlight detection
      */
    let selectionTimeout: number | null = null;

    function debouncedHandleSelection(): void {
      if (selectionTimeout) {
        clearTimeout(selectionTimeout);
      }

      selectionTimeout = window.setTimeout(() => {
        handleTextSelection();
        selectionTimeout = null;
      }, 300); // Further reduced delay for faster appearance in input
    }

    // Setup event listeners for text selection
    console.log('[Content] Setting up text selection listeners');

    // Mouse and keyboard events for text selection
    document.addEventListener('mouseup', debouncedHandleSelection);
    document.addEventListener('keyup', debouncedHandleSelection);
    document.addEventListener('dblclick', debouncedHandleSelection);
    document.addEventListener('contextmenu', debouncedHandleSelection);

    // Page visibility change
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        debouncedHandleSelection();
      }
    });



    console.log('[Content] Content script initialized');
  },
});