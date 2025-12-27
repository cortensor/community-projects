// src/app/page.tsx
"use client"

import React, { useState, useEffect, useCallback, useMemo } from "react"
import dynamic from "next/dynamic"
import { ChatStorage, type ChatSession, type ChatMessage } from "@/lib/storage"
import { SlidingPanel } from "@/components/sliding-panel"
import { MainContent } from "@/components/main-content"
import { ChatInput } from "@/components/chat-input"
import { ModelChangeDialog } from "@/components/model-change-dialog"
import { StreamingThinking } from "@/components/streaming-thinking"
import { PageLoadingSkeleton, AppLoadingScreen } from "@/components/page-loading"
import { useToast } from "@/components/ui/use-toast"
import { useIsMobile } from "@/hooks/use-mobile"
import { useEnvironment } from "@/contexts/environment-context"
import { appConfig } from "@/lib/app-config"
import { frontendLogger } from "@/lib/logger"
import { getSelectedModel, setSelectedModel as saveSelectedModel } from "@/lib/environment-config"
import { ErrorBoundary } from "@/components/error-boundary"
import { cn } from "@/lib/utils"
import { BrainCircuit } from "lucide-react"

// Lazy load heavy components
const BackgroundPattern = dynamic(() => import("@/components/background-pattern").then(mod => ({ default: mod.BackgroundPattern })), {
  ssr: false,
  loading: () => null
})

function CortensorAIChatInner() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [allSessions, setAllSessions] = useState<ChatSession[]>([]); // Store all sessions regardless of model
  const [currentChatId, setCurrentChatId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const { environment, setEnvironment } = useEnvironment();
  const { toast } = useToast();
  const [isMemoryMode, setIsMemoryMode] = useState(true);
  const [selectedModel, setSelectedModelState] = useState('llama-3.1-8b-q4');
  const [isDeepThinking, setIsDeepThinking] = useState(false);
  const [isThinkingPhase, setIsThinkingPhase] = useState(false);
  const [pendingModelChange, setPendingModelChange] = useState<{
    modelId: string;
    modelName: string;
  } | null>(null);
  const [isModelChanging, setIsModelChanging] = useState(false);
  const [isConfirmingModelChange, setIsConfirmingModelChange] = useState(false);
  const [sessionSort, setSessionSort] = useState<'recent' | 'unread'>('recent');
  const isMobile = useIsMobile();

  // Helper function to save current model sessions while preserving others
  const saveModelSessions = useCallback((currentModelSessions: ChatSession[]) => {
    try {
      const allSessionsFromStorage = ChatStorage.loadSessions();
      const otherModelSessions = allSessionsFromStorage.filter(s => s.selectedModel !== selectedModel);
      const updatedAllSessions = [...otherModelSessions, ...currentModelSessions];
      
      if (!ChatStorage.saveSessions(updatedAllSessions)) {
        frontendLogger.error('Failed to save sessions');
        return false;
      }
      
      // Update both current model sessions and all sessions state
      setAllSessions(updatedAllSessions);
      
      frontendLogger.debug('Successfully saved sessions', { 
        totalSessions: updatedAllSessions.length,
        currentModelSessions: currentModelSessions.length,
        otherModelSessions: otherModelSessions.length
      });
      return true;
    } catch (error) {
      frontendLogger.error('Error saving sessions', error);
      return false;
    }
  }, [selectedModel]);

  // Utility function to cleanup DOM state after model changes
  const cleanupDOMState = useCallback(() => {
    try {
      // Remove any problematic aria-hidden attributes
      document.querySelectorAll('[aria-hidden="true"]').forEach(el => {
        const element = el as HTMLElement;
        if (element.contains(document.activeElement)) {
          element.removeAttribute('aria-hidden');
        }
      });
      
      // Clear modal/dialog body styles
      document.body.style.pointerEvents = '';
      document.body.style.overflow = '';
      document.body.removeAttribute('aria-hidden');
      
      // Handle focus cleanup
      if (document.activeElement instanceof HTMLElement && 
          document.activeElement !== document.body) {
        document.activeElement.blur();
      }
      
      // Focus safe element
      const mainElement = document.querySelector('main');
      if (mainElement instanceof HTMLElement) {
        mainElement.focus();
      }
      
      frontendLogger.debug('DOM state cleanup completed');
    } catch (error) {
      frontendLogger.error('DOM cleanup failed', error);
    }
  }, []);

  // Generate unique ID to prevent collisions
  const generateUniqueId = useCallback(() => {
    return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Wrapper function untuk persist model selection
  const updateSelectedModel = useCallback((modelId: string) => {
    try {
      frontendLogger.info('Updating selected model', { 
        from: selectedModel, 
        to: modelId 
      });
      
      // Validate model exists before updating
      const modelExists = appConfig.chat.models.find(m => m.id === modelId);
      if (!modelExists) {
        throw new Error(`Model ${modelId} not found in app config`);
      }

      // Apply model presets (prompt, deep thinking, memory)
      if (modelExists.preset) {
        setIsDeepThinking(!!modelExists.preset.deepThinking);
        setIsMemoryMode(modelExists.preset.memory !== false);
        if (modelExists.preset.prompt && !input.trim()) {
          setInput(modelExists.preset.prompt);
        }
      }
      
      // Safe model update with timeout protection
      const updateTimer = setTimeout(() => {
        frontendLogger.error('Model update timed out', { modelId });
      }, 5000);
      
      // Update both state AND localStorage
      setSelectedModelState(modelId); // Update React state
      saveSelectedModel(modelId); // Update localStorage - CRITICAL!
      
      clearTimeout(updateTimer);
      
      frontendLogger.debug('Model updated successfully', { 
        newModelId: modelId,
        modelName: modelExists.name 
      });
      
      // Load and filter sessions for the new model
      const allSessionsFromStorage = ChatStorage.loadSessions();
      const modelSessions = allSessionsFromStorage.filter(session => session.selectedModel === modelId);
      
      // Update both filtered sessions and all sessions
      setSessions(modelSessions);
      setAllSessions(allSessionsFromStorage);
      
      if (modelSessions.length > 0) {
        // Load the last active session for this model
        const lastActiveId = localStorage.getItem(`lastActiveSessionId_${modelId}`);
        const sessionToLoad = modelSessions.find(s => s.id === lastActiveId) || modelSessions[modelSessions.length - 1];
        setCurrentChatId(sessionToLoad.id);
        setMessages(sessionToLoad.messages);
        frontendLogger.info('Loaded sessions for new model', {
          modelId,
          totalModelSessions: modelSessions.length,
          loadedSessionId: sessionToLoad.id
        });
      } else {
        // No sessions for this model, create a new one
        const selectedModelData = appConfig.chat.models.find(m => m.id === modelId);
        const newChat: ChatSession = {
          id: generateUniqueId(),
          cortensorSessionId: selectedModelData?.sessionId || appConfig.chat.staticSessionId,
          title: "New Chat",
          messages: [],
          selectedModel: modelId,
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        setSessions([newChat]);
        setAllSessions(prev => [...prev, newChat]); // Also add to allSessions
        setCurrentChatId(newChat.id);
        setMessages([]);
        
        // Save to localStorage
        const allSessionsWithNew = [...ChatStorage.loadSessions(), newChat];
        ChatStorage.saveSessions(allSessionsWithNew);
        
        frontendLogger.info('Created new session for model', {
          modelId,
          newSessionId: newChat.id
        });
      }
      
    } catch (error) {
      frontendLogger.error('Failed to update model', { 
        modelId, 
        error: error instanceof Error ? error.message : 'Unknown error' 
      });
      throw error; // Re-throw to handle in calling function
    }
  }, [generateUniqueId]);

  // Handle environment change
  const handleEnvironmentChange = useCallback((newEnv: typeof environment) => {
    setEnvironment(newEnv);
    
    // Show toast notification
    toast({
      title: "Environment Changed",
      description: `Switched to ${newEnv === 'testnet' ? 'Testnet0' : 'Devnet-7'}. Changes will apply to new messages.`,
      duration: 3000,
    });
  }, [setEnvironment, toast, environment]);

  // Close panel on mobile by default
  useEffect(() => {
    if (isMobile) {
      setIsPanelOpen(false);
    } else {
      setIsPanelOpen(true);
    }
  }, [isMobile]);

  const handleModelChange = useCallback((modelId: string, modelName: string) => {
    // Prevent rapid clicking during model change
    if (isModelChanging) {
      frontendLogger.warn('Model change already in progress, ignoring request');
      return;
    }
    
    if (modelId === selectedModel) {
      frontendLogger.debug('Same model selected, no change needed', { modelId });
      return;
    }
    
    setIsModelChanging(true);
    
    try {
      frontendLogger.info('Initiating model change', { 
        from: selectedModel, 
        to: modelId, 
        modelName,
        currentChatId: currentChatId,
        messagesCount: messages ? messages.length : 0,
        hasMessages: !!(messages && messages.length > 0)
      });
      
      // Clear any existing pending changes
      if (pendingModelChange) {
        frontendLogger.debug('Clearing previous pending model change');
        setPendingModelChange(null);
      }
      
      // If there are active messages in the current chat, show confirmation
      const hasActiveMessages = messages && messages.length > 0;
      if (hasActiveMessages) {
        frontendLogger.debug('Active messages detected, showing confirmation dialog', {
          messagesCount: messages.length,
          currentChatId: currentChatId
        });
        setPendingModelChange({ modelId, modelName });
      } else {
        frontendLogger.debug('No active messages, directly updating model');
        // Direct model update for empty chats
        try {
          updateSelectedModel(modelId);
          toast({ 
            title: "Model Changed", 
            description: `Now using ${modelName}` 
          });
          frontendLogger.info('Direct model change completed', { 
            newModel: modelId, 
            modelName 
          });
        } catch (updateError) {
          frontendLogger.error('Direct model update failed', updateError);
          throw updateError;
        }
      }
    } catch (error) {
      frontendLogger.error('Error during model change initiation', error);
      toast({
        title: "Model Change Failed",
        description: "Failed to change model. Please try again.",
        variant: "destructive"
      });
    } finally {
      // Reset the flag after a short delay
      setTimeout(() => {
        setIsModelChanging(false);
        frontendLogger.debug('Model changing flag reset');
      }, 1000);
    }
  }, [selectedModel, messages, pendingModelChange, updateSelectedModel, toast, isModelChanging, currentChatId]);

  // Helper function to remove duplicate sessions by ID
  const removeDuplicateSessions = useCallback((sessions: ChatSession[]) => {
    const seen = new Set<string>();
    return sessions.filter(session => {
      if (seen.has(session.id)) {
        frontendLogger.warn('Removing duplicate session', { sessionId: session.id });
        return false;
      }
      seen.add(session.id);
      return true;
    });
  }, []);

  const handleConfirmModelChange = useCallback(async () => {
    if (!pendingModelChange) {
      frontendLogger.warn('No pending model change to confirm');
      return;
    }
    
    if (isConfirmingModelChange) {
      frontendLogger.warn('Model change confirmation already in progress');
      return;
    }
    
    try {
      setIsConfirmingModelChange(true);
      
      // Clear any storage conflicts before starting
      ChatStorage.clearStorageConflicts();
      
      frontendLogger.info('Confirming model change', { 
        from: selectedModel, 
        to: pendingModelChange.modelId,
        pendingModelName: pendingModelChange.modelName,
        currentChatId: currentChatId,
        messagesCount: messages.length
      });
      
      // Get the selected model data and validate session ID
      const selectedModelData = appConfig.chat.models.find(m => m.id === pendingModelChange.modelId);
      
      if (!selectedModelData) {
        throw new Error(`Model configuration not found for: ${pendingModelChange.modelId}`);
      }
      
      const sessionId = selectedModelData.sessionId;
      if (!sessionId) {
        throw new Error(`Session ID not configured for model: ${pendingModelChange.modelId}`);
      }
      
      frontendLogger.debug('Model validation successful', {
        modelId: pendingModelChange.modelId,
        sessionId: sessionId,
        modelName: selectedModelData.name
      });
      
      // Simplified approach: Just update the model, updateSelectedModel will handle session creation
      setPendingModelChange(null);
      setMessages([]);
      
      // Update the model - this will automatically create a new session if needed
      updateSelectedModel(pendingModelChange.modelId);
      
      frontendLogger.info('Successfully completed model change', { 
        modelId: pendingModelChange.modelId,
        modelName: pendingModelChange.modelName
      });
      
      toast({ 
        title: "Model Changed", 
        description: `Started new chat with ${pendingModelChange?.modelName}` 
      });
      
      // Reset loading state
      setIsConfirmingModelChange(false);
      
      // Final DOM cleanup after success
      setTimeout(() => {
        cleanupDOMState();
      }, 300);
      
    } catch (error) {
      frontendLogger.error('Error during model change confirmation', error);
      
      // Aggressive cleanup on error to prevent freeze
      try {
        cleanupDOMState();
      } catch (cleanupError) {
        frontendLogger.error('Cleanup error', cleanupError);
      }
      
      toast({
        title: "Model Change Failed",
        description: error instanceof Error ? error.message : "Failed to change model. Please try again.",
        variant: "destructive"
      });
      setPendingModelChange(null);
      setIsConfirmingModelChange(false);
    }
  }, [pendingModelChange, updateSelectedModel, toast, isConfirmingModelChange]);

  const handleCancelModelChange = useCallback(() => {
    // Prevent canceling while loading
    if (isConfirmingModelChange) {
      frontendLogger.warn('Cannot cancel model change while loading');
      return;
    }
    setPendingModelChange(null);
  }, [isConfirmingModelChange]);

  const handleNewChat = useCallback(() => {
    const selectedModelData = appConfig.chat.models.find(m => m.id === selectedModel);
    const newChat: ChatSession = {
      id: generateUniqueId(),
      cortensorSessionId: selectedModelData?.sessionId || appConfig.chat.staticSessionId,
      title: "New Chat",
      messages: [],
      selectedModel: selectedModel,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    setSessions(prev => {
      const updated = [...prev, newChat];
      saveModelSessions(updated);
      return updated;
    });
    
    // Also update allSessions
    setAllSessions(prev => [...prev, newChat]);
    
    setCurrentChatId(newChat.id);
    setMessages([]);
    frontendLogger.info('New chat created', { chatId: newChat.id, model: selectedModel });
    toast({ title: "New chat started." });
  }, [selectedModel, toast, saveModelSessions, generateUniqueId]);

  useEffect(() => {
    // Log initial load/reload for visibility in console
    try {
      const navEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
      const navType = navEntry?.type || (performance as any).navigation?.type;
      frontendLogger.info('Page load event', {
        navType: typeof navType === 'number' ? navType : navType || 'unknown',
        path: window.location.pathname,
        search: window.location.search,
      });
    } catch (error) {
      frontendLogger.warn('Navigation log failed', { error });
    }

    const initializeApp = async () => {
      try {
        frontendLogger.info('Initializing application');
        // Show loading animation for better UX - optimized duration
        await new Promise(resolve => setTimeout(resolve, 800));
        
        // Load saved model selection first
        const savedModel = getSelectedModel();
        // Direct state update to avoid circular dependency
        setSelectedModelState(savedModel);
        saveSelectedModel(savedModel);
        
        // Load user data and initialize
        let localHistories = ChatStorage.loadSessions();
        
        // Migrate existing sessions to include selectedModel
        let needsMigration = false;
        const migratedHistories = localHistories.map(session => {
          if (!session.selectedModel) {
            needsMigration = true;
            return {
              ...session,
              selectedModel: 'llama-3.1-8b-q4' // Default to Meta-Llama 3.1 8B Q4
            };
          }
          return session;
        });
        
        if (needsMigration) {
          frontendLogger.info('Migrating sessions to include selectedModel');
          ChatStorage.saveSessions(migratedHistories);
          localHistories = migratedHistories;
        }
        
        // Remove any duplicate sessions
        const cleanedHistories = removeDuplicateSessions(localHistories);
        if (cleanedHistories.length !== localHistories.length) {
          frontendLogger.info('Cleaned duplicate sessions', { 
            before: localHistories.length, 
            after: cleanedHistories.length 
          });
          ChatStorage.saveSessions(cleanedHistories);
          localHistories = cleanedHistories;
        }
        
        // Filter sessions by selected model
        const modelSessions = localHistories.filter(session => session.selectedModel === savedModel);
        
        // Update both filtered sessions and all sessions
        setAllSessions(localHistories);
        
        if (modelSessions.length > 0) {
          setSessions(modelSessions);
          const lastActiveId = localStorage.getItem(`lastActiveSessionId_${savedModel}`);
          const sessionToLoad = modelSessions.find(s => s.id === lastActiveId) || modelSessions[modelSessions.length - 1];
          setCurrentChatId(sessionToLoad.id);
          setMessages(sessionToLoad.messages);
          // JANGAN timpa model selection user dengan model dari session lama
          // Tetap gunakan savedModel yang dipilih user
          frontendLogger.info('Loaded existing sessions for model', { 
            totalSessions: localHistories.length,
            modelSessions: modelSessions.length,
            activeSessionId: sessionToLoad.id,
            selectedModel: savedModel // Use user's selection, not session's model
          });
          const currentModel = appConfig.chat.models.find(m => m.id === savedModel);
          if (currentModel?.preset) {
            setIsDeepThinking(!!currentModel.preset.deepThinking);
            setIsMemoryMode(currentModel.preset.memory !== false);
            if (currentModel.preset.prompt && !input.trim()) {
              setInput(currentModel.preset.prompt);
            }
          }
        } else {
          frontendLogger.info('No existing sessions found, creating new chat');
          // Create new chat inline to avoid circular dependency
          const selectedModelData = appConfig.chat.models.find(m => m.id === savedModel);
          const newChat: ChatSession = {
            id: generateUniqueId(),
            cortensorSessionId: selectedModelData?.sessionId || appConfig.chat.staticSessionId,
            title: "New Chat",
            messages: [],
            selectedModel: savedModel,
            createdAt: new Date(),
            updatedAt: new Date(),
          };
          setSessions([newChat]);
          setAllSessions([newChat]);
          setCurrentChatId(newChat.id);
          setMessages([]);
          if (!ChatStorage.saveSessions([newChat])) {
            frontendLogger.error('Failed to save initial session');
          }
          frontendLogger.info('Initial chat created', { chatId: newChat.id, model: savedModel });
        }
      } catch (error) {
        frontendLogger.error('Failed to initialize app', error);
        // Use toast directly without adding to dependencies
        if (toast) {
          toast({
            title: "Initialization Error", 
            description: "Failed to load chat history. Starting fresh.",
            variant: "destructive"
          });
        }
        // Fallback new chat creation
        const newChat: ChatSession = {
          id: generateUniqueId(),
          cortensorSessionId: appConfig.chat.staticSessionId,
          title: "New Chat",
          messages: [],
          selectedModel: 'llama-3.1-8b-q4',
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        setSessions([newChat]);
        setCurrentChatId(newChat.id);
        setMessages([]);
      } finally {
        setIsPageLoading(false);
      }
    };

    // Only run once on mount
    initializeApp();
  }, [generateUniqueId, removeDuplicateSessions]); // Add necessary dependencies

  const loadLocalChat = useCallback((chatId: string) => {
    // First try to find in current sessions
    let session = sessions.find(s => s.id === chatId);
    
    // If not found in current sessions, search all sessions
    if (!session) {
      session = allSessions.find(s => s.id === chatId);
      
      if (session) {
        // Session found but not in current filtered list
        // Check if we need to switch models or just load the session
        if (session.selectedModel !== selectedModel) {
          frontendLogger.info('Loading session from different model', {
            sessionModel: session.selectedModel,
            currentModel: selectedModel,
            chatId
          });
          
          // Switch to the session's model first
          updateSelectedModel(session.selectedModel);
          
          // Use a Promise-based approach instead of setTimeout for better reliability
          Promise.resolve().then(() => {
            setCurrentChatId(chatId);
            setMessages(session!.messages);
            localStorage.setItem(`lastActiveSessionId_${session!.selectedModel}`, chatId);
            frontendLogger.info('Loaded cross-model session', {
              chatId,
              messageCount: session!.messages.length,
              switchedToModel: session!.selectedModel
            });
          });
          return;
        }
      }
    }
    
    if (session) {
      setCurrentChatId(chatId);
      setMessages(session.messages);
      localStorage.setItem(`lastActiveSessionId_${session.selectedModel}`, chatId);
      frontendLogger.debug('Loaded chat session', { 
        chatId, 
        messageCount: session.messages.length,
        model: session.selectedModel, // Use session's model, not current selectedModel
        currentSelectedModel: selectedModel
      });
    } else {
      frontendLogger.warn('Attempted to load non-existent chat', { chatId });
    }
  }, [sessions, allSessions, selectedModel, updateSelectedModel]);

  const handleDeleteSession = useCallback((chatId: string) => {
    const updatedSessions = sessions.filter(s => s.id !== chatId);
    const updatedAllSessions = allSessions.filter(s => s.id !== chatId);
    
    setSessions(updatedSessions);
    setAllSessions(updatedAllSessions);
    
    // Save to localStorage
    ChatStorage.saveSessions(updatedAllSessions);
    
    if (currentChatId === chatId) {
      if (updatedSessions.length > 0) {
        loadLocalChat(updatedSessions[updatedSessions.length - 1].id);
      } else {
        handleNewChat();
      }
    }
    
    frontendLogger.info('Session deleted', { chatId, remainingSessions: updatedSessions.length, totalSessions: updatedAllSessions.length });
  }, [sessions, allSessions, currentChatId, loadLocalChat, handleNewChat]);

  const sendMessage = useCallback(async (messageText: string, enableMemory: boolean = isMemoryMode) => {
    const trimmedMessage = messageText.trim();
    if (!trimmedMessage) {
      frontendLogger.warn('Attempted to send empty message');
      return;
    }

    if (isLoading) {
      frontendLogger.warn('Message ignored - already processing');
      return;
    }

    // Add timestamp to prevent duplicate requests
    const requestId = Date.now().toString();
    frontendLogger.info('Sending message', { 
      requestId, 
      messageLength: trimmedMessage.length,
      model: selectedModel, 
      environment, 
      isDeepThinking, 
      streamingMode: 'enabled-with-text-extraction',
      textExtractionEnabled: true
    });

    const userMessage: ChatMessage = {
      id: requestId,
      content: trimmedMessage,
      role: 'user',
      timestamp: new Date(),
    };

    // Update UI immediately
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    
    // For DeepSeek R1, don't start with thinking phase since responses don't use <think> tags
    if (selectedModel.includes('deepseek-r1')) {
      setIsThinkingPhase(false); // Don't start thinking phase
      setIsLoading(true); // Use regular loading initially
    } else {
      setIsLoading(true);
    }

    try {
      const selectedModelData = appConfig.chat.models.find(m => m.id === selectedModel);
      const sessionId = selectedModelData?.sessionId || appConfig.chat.staticSessionId;
      
      // Include latest user turn in history when memory mode is enabled
      const historyToSend = enableMemory ? [...messages, userMessage] : [];

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-chat-environment': environment,
        },
        body: JSON.stringify({
          message: trimmedMessage,
          sessionId: sessionId,
          enableMemory,
          model: selectedModel,
          isDeepThinking,
          showThinkingProcess: selectedModel.includes('deepseek-r1'), // Always true for DeepSeek
          chatHistory: historyToSend,
          environment: environment,
          // Stream for Llama, non-stream for others
          nonStreaming: selectedModel === 'llama-3.1-8b-q4' ? false : true
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API request failed: ${response.status} ${response.statusText}. ${errorText}`);
      }

      // If API returns JSON (non-stream), parse once and finish
      const contentType = response.headers.get('Content-Type') || '';
      if (contentType.includes('application/json')) {
        const data = await response.json();
        let contentText: string = (data?.content || data?.response || data?.text || '').toString();
        let thinkingText: string | undefined = data?.thinkingContent;

        // Summarize DeepSeek thinking in English for display
        const summarizeThinking = (thinking: string, userMsg: string): string => {
          const clean = (thinking || '').replace(/\s+/g, ' ').trim();
          if (!clean) return '';
          const um = (userMsg || '').trim();
          const firstSentence = clean.split(/(?<=[.!?])\s+/)[0]?.slice(0, 160) || '';
          const lc = clean.toLowerCase();
          const bullets: string[] = [];
          const ctxSnippet = (um || firstSentence).replace(/^[\u2212\-•\s]+/, '').slice(0, 160);
          bullets.push('Thinking summary:');
          bullets.push(`- Context: ${ctxSnippet}`);
          if (/(step|plan|approach|strategy|first|second|third|1\.|2\.|3\.)/i.test(lc)) bullets.push('- Laying out a solution plan');
          if (/(assumption|assume|if|suppose)/i.test(lc)) bullets.push('- Establishing key assumptions');
          if (/(risk|edge\s*case|limitation|constraint|ambiguity)/i.test(lc)) bullets.push('- Considering risks and limitations');
          if (/(check|validate|relevant|compare|verify|confirm)/i.test(lc)) bullets.push('- Validating relevance and consistency');
          if (/(formula|compute|calculate|estimation|derivation|reasoning)/i.test(lc)) bullets.push('- Performing calculations/reasoning');
        
          const seen = new Set<string>();
          const capped = bullets.filter(b => !seen.has(b) && (seen.add(b), true)).slice(0, 8);
          return capped.join('\n');
        };

        if (selectedModel.includes('deepseek-r1') && thinkingText) {
          thinkingText = summarizeThinking(thinkingText, trimmedMessage);
        }

        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          content: contentText,
          role: 'assistant',
          timestamp: new Date(),
          ...(thinkingText ? { thinkingContent: thinkingText } : {})
        };

        // Append assistant message
        let finalMessages: ChatMessage[] = [];
        setMessages(prev => {
          const updated = [...prev, assistantMessage];
          finalMessages = updated;
          return updated;
        });

        // Update session storage
        const currentSession = sessions.find(s => s.id === currentChatId);
        const updatedSession: ChatSession = {
          id: currentChatId,
          cortensorSessionId: selectedModelData?.sessionId || appConfig.chat.staticSessionId,
          title: userMessage.content.slice(0, 50) + "..." || "New Chat",
          messages: finalMessages.filter(m => m.role === 'user' || m.role === 'assistant'),
          selectedModel: currentSession?.selectedModel || selectedModel,
          createdAt: currentSession?.createdAt || new Date(),
          updatedAt: new Date(),
        };

        setSessions(prevSessions => {
          const updatedSessions = prevSessions.map(s => s.id === currentChatId ? updatedSession : s);
          saveModelSessions(updatedSessions);
          return updatedSessions;
        });
        setAllSessions(prevAllSessions => prevAllSessions.map(s => s.id === currentChatId ? updatedSession : s));

        setIsLoading(false);
        setIsThinkingPhase(false);
        return; // Exit early; non-stream path complete
      }

      // Handle streaming response with text extraction
      if (!response.body) {
        throw new Error('No response body available');
      }

      let assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: '',
        role: 'assistant',
        timestamp: new Date(),
        ...(selectedModel.includes('deepseek-r1') && { thinkingContent: '' }) // Add thinking content for DeepSeek
      };

      setMessages(prev => [...prev, assistantMessage]);
      setIsThinkingPhase(isDeepThinking && selectedModel === 'deepseek-r1');
      
      // Process streaming response with timeout protection
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';
      
      // Timeout protection for streaming
      const streamingTimeout = setTimeout(() => {
        frontendLogger.error('Streaming timeout - forcing completion');
        setIsLoading(false);
        setIsThinkingPhase(false);
        reader.cancel();
      }, 120000); // 2 minute timeout
      
      frontendLogger.info('Starting streaming response processing', {
        hasReader: !!reader,
        responseType: response.headers.get('X-Response-Type'),
        contentType: response.headers.get('Content-Type')
      });
      
      try {
        // Helper: Summarize DeepSeek thinking into readable English steps
        const summarizeDeepSeekThinking = (thinking: string, userMessage: string): string => {
          const clean = (thinking || '').replace(/\s+/g, ' ').trim();
          if (!clean) return '';
          const um = (userMessage || '').trim();
          const firstSentence = clean.split(/(?<=[.!?])\s+/)[0]?.slice(0, 160) || '';
          const lc = clean.toLowerCase();
          const bullets: string[] = [];
          const ctxSnippet = (um || firstSentence).replace(/^[-•\s]+/, '').slice(0, 160);
          bullets.push(`Thinking summary:`);
          bullets.push(`- Context: ${ctxSnippet}`);
          if (/(step|plan|approach|strategy|first|second|third|1\.|2\.|3\.)/i.test(lc)) {
            bullets.push('- Laying out a solution plan');
          }
          if (/(assumption|assume|if|suppose)/i.test(lc)) {
            bullets.push('- Establishing key assumptions');
          }
          if (/(risk|edge\s*case|limitation|constraint|ambiguity)/i.test(lc)) {
            bullets.push('- Considering risks and limitations');
          }
          if (/(check|validate|relevant|compare|verify|confirm)/i.test(lc)) {
            bullets.push('- Validating relevance and consistency');
          }
          if (/(formula|compute|calculate|estimation|derivation|reasoning)/i.test(lc)) {
            bullets.push('- Performing calculations/reasoning');
          }
          // Always conclude with formulating the answer
          bullets.push('- Formulating a clear and concise answer');
          // Deduplicate and cap
          const seen = new Set<string>();
          const capped = bullets.filter(b => !seen.has(b) && (seen.add(b), true)).slice(0, 6);
          return `Thinking summary:\n- ${capped.join('\n- ')}`;
        };
        while (true) {
          const { done, value } = await reader.read();
          
          frontendLogger.debug('Received streaming chunk', { 
            done, 
            chunkSize: value ? value.length : 0 
          });
          
          if (done) {
            frontendLogger.info('Streaming completed', { 
              totalContentLength: accumulatedContent.length,
              finalContent: accumulatedContent.substring(0, 100) + (accumulatedContent.length > 100 ? '...' : '')
            });
            // Ensure loading state is reset when streaming completes
            setIsLoading(false);
            setIsThinkingPhase(false);
            break;
          }
          
          const chunk = decoder.decode(value, { stream: true });
          frontendLogger.debug('Decoded chunk', { 
            chunkContent: chunk.substring(0, 100) + (chunk.length > 100 ? '...' : ''),
            chunkLength: chunk.length
          });
          
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              
              frontendLogger.debug('Processing SSE data', { 
                data: data.substring(0, 200) + (data.length > 200 ? '...' : '')
              });
              
              if (data === '[DONE]') {
                frontendLogger.info('Received DONE signal');
                setIsThinkingPhase(false);
                break;
              }
              
              try {
                const parsed = JSON.parse(data);
                
                // Extract content from streaming response - Updated for Cortensor format
                let newContent = '';
                
                // Handle Cortensor API format (choice.text)
                if (parsed.choices && parsed.choices[0] && parsed.choices[0].text) {
                  newContent = parsed.choices[0].text;
                  frontendLogger.debug('Extracted content from Cortensor format', { 
                    contentValue: newContent,
                    contentLength: newContent.length
                  });
                }
                // Handle OpenAI format (delta.content) - fallback
                else if (parsed.choices && parsed.choices[0] && parsed.choices[0].delta && parsed.choices[0].delta.content) {
                  newContent = parsed.choices[0].delta.content;
                  frontendLogger.debug('Extracted content from OpenAI format', { 
                    contentValue: newContent,
                    contentLength: newContent.length
                  });
                }
                // Handle direct content field
                else if (parsed.content) {
                  newContent = parsed.content;
                  frontendLogger.debug('Extracted content from direct field', { 
                    contentValue: newContent,
                    contentLength: newContent.length
                  });
                }
                
                frontendLogger.debug('Content extraction result', { 
                  hasContent: !!newContent,
                  contentLength: newContent.length,
                  contentValue: newContent,
                  contentPreview: newContent.substring(0, 50),
                  parsedStructure: {
                    hasChoices: !!parsed.choices,
                    hasDelta: !!(parsed.choices && parsed.choices[0] && parsed.choices[0].delta),
                    hasDirectContent: !!parsed.content
                  }
                });
                
                if (newContent) {
                  accumulatedContent += newContent;
                  
                  frontendLogger.debug('Content accumulation', { 
                    newContentLength: newContent.length,
                    newContentValue: newContent,
                    totalAccumulatedLength: accumulatedContent.length,
                    accumulatedPreview: accumulatedContent.substring(0, 100)
                  });
                  
                  // Parse content for DeepSeek R1 thinking process
                  let displayContent = accumulatedContent;
                  let thinkingContent = '';
                  let isThinkingComplete = false;
                  
                  // For DeepSeek R1 model with thinking process feature
                  if (selectedModel.includes('deepseek-r1')) {
                    // Look for </think> tag to mark end of thinking process
                    const thinkEndIndex = accumulatedContent.indexOf('</think>');
                    
                    if (thinkEndIndex > -1) {
                      // Thinking process is complete with explicit tag
                      isThinkingComplete = true;
                      thinkingContent = accumulatedContent.substring(0, thinkEndIndex).trim();
                      displayContent = accumulatedContent.substring(thinkEndIndex + 8).trim(); // Skip </think>
                      
                      // Clean up any remaining markers
                      displayContent = displayContent.replace(/^[\n\r]+/, '');
                      setIsThinkingPhase(false); // Stop thinking phase
                    } else {
                      // DeepSeek R1 doesn't use <think> tags - treat entire response as content
                      // For now, show everything as main content since no thinking separator found
                      displayContent = accumulatedContent;
                      thinkingContent = '';
                      setIsThinkingPhase(false); // No explicit thinking, just show content
                    }
                    
                    // Cleanup thinking content for proper display
                    if (thinkingContent) {
                      thinkingContent = thinkingContent
                        .replace(/^<think>\s*/i, '')
                        .replace(/<\|USER\|>|<\|ASSISTANT\|>/gi, '')
                        .replace(/^\s*(user|assistant)\s*:\s*/gi, '')
                        .replace(/<\|begin_of_text\|>|<\|end_of_text\|>|<\|eot_id\|>/gi, '')
                        .replace(/<｜end▁of▁sentence｜>/g, '')
                        .replace(/<\|end_of_sentence\|>/g, '')
                        .trim();
                      // Convert raw thinking into readable steps
                      thinkingContent = summarizeDeepSeekThinking(thinkingContent, trimmedMessage);
                    }
                  }
                  
                  // Update the assistant message with separated content
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantMessage.id 
                      ? { 
                          ...msg, 
                          content: displayContent,
                          thinkingContent: thinkingContent
                        }
                      : msg
                  ));
                  
                  frontendLogger.debug('Updated message content', { 
                    totalLength: accumulatedContent.length,
                    displayLength: displayContent.length,
                    thinkingLength: thinkingContent.length,
                    hasThinking: accumulatedContent.includes('</think>')
                  });
                }
              } catch (parseError) {
                frontendLogger.warn('Failed to parse SSE data', { 
                  parseError, 
                  data: data.substring(0, 100) 
                });
                // Skip invalid JSON chunks
                continue;
              }
            }
          }
        }
      } catch (streamError) {
        frontendLogger.error('Streaming error', streamError);
        throw new Error('Failed to process streaming response');
      } finally {
        clearTimeout(streamingTimeout);
        reader.releaseLock();
      }

      setIsThinkingPhase(false);

      // Safety check: Ensure the assistant message has content
      setMessages(prev => {
        const assistantMsg = prev.find(m => m.id === assistantMessage.id);
        if (assistantMsg && !assistantMsg.content.trim()) {
          console.warn('⚠️ Assistant message is empty, this might indicate a response processing issue');
          return prev.map(msg => 
            msg.id === assistantMessage.id 
              ? { ...msg, content: "I apologize, but there was an issue processing the response. Please try again." }
              : msg
          );
        }
        return prev;
      });

      // Update session with the new messages
      setMessages(prev => {
        const currentAssistantMessage = prev.find(m => m.id === assistantMessage.id);
        if (!currentAssistantMessage) {
          return prev;
        }

        // Update session with the new messages (no deduplication needed)
        const currentSession = sessions.find(s => s.id === currentChatId);
        const selectedModelData = appConfig.chat.models.find(m => m.id === selectedModel);
        const updatedSession: ChatSession = {
          id: currentChatId,
          cortensorSessionId: selectedModelData?.sessionId || appConfig.chat.staticSessionId,
          title: userMessage.content.slice(0, 50) + "..." || "New Chat",
          messages: prev.filter(m => m.role === 'user' || m.role === 'assistant'),
          selectedModel: currentSession?.selectedModel || selectedModel, // Preserve original model or use current
          createdAt: currentSession?.createdAt || new Date(),
          updatedAt: new Date(),
        };

        setSessions(prevSessions => {
          const updatedSessions = prevSessions.map(s => s.id === currentChatId ? updatedSession : s);
          saveModelSessions(updatedSessions);
          return updatedSessions;
        });
        
        // Also update allSessions
        setAllSessions(prevAllSessions => {
          return prevAllSessions.map(s => s.id === currentChatId ? updatedSession : s);
        });

        frontendLogger.info('Message exchange completed successfully', {
          userMessageLength: userMessage.content.length,
          assistantMessageLength: currentAssistantMessage.content.length,
          totalMessages: prev.length
        });

        return prev; // Return the messages as-is
      });

    } catch (error) {
      frontendLogger.error('Error sending message', error);
      
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
      
      setMessages(prev => [...prev.slice(0, -1), {
        id: (Date.now() + 1).toString(),
        content: `❌ **Error**: ${errorMessage}\n\nPlease try again or contact support if the issue persists.`,
        role: 'assistant',
        timestamp: new Date(),
        isError: true
      }]);

      toast({
        title: "Message Error",
        description: errorMessage,
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
      setIsThinkingPhase(false);
    }
  }, [messages, isLoading, isMemoryMode, selectedModel, isDeepThinking, currentChatId, sessions, toast, environment]);

  const handleSubmit = useCallback((e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (input.trim()) {
      frontendLogger.info('Submit triggered', {
        chatId: currentChatId,
        model: selectedModel,
        environment,
        length: input.trim().length
      });
      sendMessage(input.trim());
    }
  }, [input, sendMessage, currentChatId, selectedModel, environment]);

  const handleTemplateInsert = useCallback((text: string) => {
    setInput(prev => prev ? `${prev}\n\n${text}` : text);
  }, []);

  const handleAttachContext = useCallback(async () => {
    try {
      if (!navigator.clipboard?.readText) {
        toast({ title: "Clipboard unavailable", description: "Clipboard API not supported.", variant: "destructive" });
        return;
      }
      const content = await navigator.clipboard.readText();
      if (!content) {
        toast({ title: "No clipboard content", description: "Clipboard is empty." });
        return;
      }
      const template = `Please summarize this context:\n${content}\n\nKeep it concise.`;
      setInput(template);
      toast({ title: "Context attached", description: "Clipboard content pasted into input." });
    } catch (error) {
      frontendLogger.error('Attach context failed', { error });
      toast({ title: "Attach failed", description: "Could not read clipboard.", variant: "destructive" });
    }
  }, [toast]);

  // Memoize deduplication to avoid running on every render
  const deduplicatedSessions = useMemo(() => {
    const cleaned = removeDuplicateSessions(allSessions);
    if (sessionSort === 'recent') {
      return cleaned.slice().sort((a, b) => {
        const at = new Date(a.updatedAt || a.createdAt || 0).getTime();
        const bt = new Date(b.updatedAt || b.createdAt || 0).getTime();
        return bt - at;
      });
    }
    // unread-first: sessions where last message is assistant (user has not replied) bubble to top
    return cleaned.slice().sort((a, b) => {
      const lastA = a.messages?.[a.messages.length - 1];
      const lastB = b.messages?.[b.messages.length - 1];
      const aScore = lastA?.role === 'assistant' ? 1 : 0;
      const bScore = lastB?.role === 'assistant' ? 1 : 0;
      if (aScore !== bScore) return bScore - aScore;
      const at = new Date(a.updatedAt || a.createdAt || 0).getTime();
      const bt = new Date(b.updatedAt || b.createdAt || 0).getTime();
      return bt - at;
    });
  }, [allSessions, removeDuplicateSessions, sessionSort]);

  if (isPageLoading) {
    return <AppLoadingScreen />;
  }

  return (
    <ErrorBoundary>
      <div className="flex h-full min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100 dark:from-slate-950 dark:via-blue-950 dark:to-slate-950 relative">
        <BackgroundPattern />
        
        <SlidingPanel
          sessions={deduplicatedSessions} // Use memoized deduplicated sessions
          currentSessionId={currentChatId}
          onNewSession={handleNewChat}
          onLoadSession={loadLocalChat}
          onDeleteSession={handleDeleteSession}
          isOpen={isPanelOpen}
          onToggle={() => setIsPanelOpen(!isPanelOpen)}
          isMobile={isMobile}
          sortMode={sessionSort}
          onSortChange={setSessionSort}
        />

        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 flex flex-col">
            <MainContent 
              currentSession={sessions.find(s => s.id === currentChatId)}
              messages={messages}
              isLoading={isLoading}
              isPanelOpen={isPanelOpen}
              isMobile={isMobile}
              isMemoryMode={isMemoryMode}
              selectedModel={selectedModel}
              isDeepThinking={isDeepThinking}
              isThinkingPhase={isThinkingPhase}
              environment={environment}
              onMemoryModeChange={setIsMemoryMode}
              onPrefill={setInput}
            />
            
            {/* Add padding bottom to prevent content being hidden behind fixed ChatInput + Footer */}
            <div className={cn("", isMobile ? "h-32" : "h-48")} />
          </div>
        </div>

        <ChatInput
          input={input}
          isLoading={isLoading}
          isPanelOpen={isPanelOpen}
          isMobile={isMobile}
          selectedModel={selectedModel}
          isDeepThinking={isDeepThinking}
          isMemoryMode={isMemoryMode}
          onModelChange={handleModelChange}
          onDeepThinkingChange={setIsDeepThinking}
          onMemoryModeChange={setIsMemoryMode}
          onInputChange={(e) => setInput(e.target.value)}
          onSubmit={handleSubmit}
          onTemplateInsert={handleTemplateInsert}
          onAttachContext={handleAttachContext}
          disabled={isLoading || !currentChatId}
        />

        <ModelChangeDialog
          isOpen={!!pendingModelChange}
          onOpenChange={(open) => {
            // Prevent closing dialog while loading
            if (!open && !isConfirmingModelChange) {
              setPendingModelChange(null);
            }
          }}
          newModelName={pendingModelChange?.modelName || ''}
          newModelId={pendingModelChange?.modelId || ''}
          onConfirm={handleConfirmModelChange}
          onCancel={handleCancelModelChange}
          isLoading={isConfirmingModelChange}
        />
      </div>
    </ErrorBoundary>
  );
}

export default function CortensorAIChat() {
  return <CortensorAIChatInner />;
}
