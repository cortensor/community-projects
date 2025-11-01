import { useCallback, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from './redux';
import {
  selectCurrentSession,
  selectAllSessions,
  selectCurrentSessionConfig,
  selectCurrentSessionMemoryEnabled,
  selectCurrentSessionResearchMode,
  selectCurrentSessionSupportsResearch,
  selectIsSidebarOpen,
  selectIsResearchMode,
  createSession,
  addMessage,
  sendMessage,
  loadChatSessions,
  saveChatSessions,
  selectSession,
  deleteSession,
  renameSession,
  toggleSidebar,
  toggleResearchMode,
  initializeSidebar,
  updateSidebarForScreenSize,
  updateSessionConfig,
  setSessionModel,
  setSessionDomain,
  setSessionPersona,
  toggleSessionMemory,
  toggleSessionResearch,
} from '@/store/slices/chatSlice';
import {
  initializeUser,
  selectUser,
} from '@/store/slices/userSlice';
import {
  loadConfigurations,
} from '@/store/slices/configSlice';

export function useNewChat() {
  const dispatch = useAppDispatch();

  // Selectors
  const currentSession = useAppSelector(selectCurrentSession);
  const allSessions = useAppSelector(selectAllSessions);
  const isSidebarOpen = useAppSelector(selectIsSidebarOpen);
  const isResearchMode = useAppSelector(selectIsResearchMode);
  const user = useAppSelector(selectUser);
  // Session-specific configuration using memoized selectors
  const sessionConfig = useAppSelector(selectCurrentSessionConfig);
  const isMemoryEnabled = useAppSelector(selectCurrentSessionMemoryEnabled);
  const sessionResearchMode = useAppSelector(selectCurrentSessionResearchMode);
  const supportsResearch = useAppSelector(selectCurrentSessionSupportsResearch);

  // Initialize app
  useEffect(() => {
    dispatch(initializeUser());
    dispatch(loadConfigurations());
    dispatch(initializeSidebar());
  }, [dispatch]);

  // Load chat sessions when user is available
  useEffect(() => {
    if (user.userId) {
      dispatch(loadChatSessions(user.userId));
    }
  }, [user.userId, dispatch]);

  // Save sessions when they change
  useEffect(() => {
    if (user.userId && allSessions.length > 0) {
      const sessionsObject = allSessions.reduce((acc, session) => {
        acc[session.id] = session;
        return acc;
      }, {} as Record<string, any>);

      dispatch(saveChatSessions({ userId: user.userId, sessions: sessionsObject }));
    }
  }, [user.userId, allSessions, dispatch]);

  // Handle screen size changes for responsive sidebar
  useEffect(() => {
    const handleResize = () => {
      dispatch(updateSidebarForScreenSize({ width: window.innerWidth }));
    };

    // Set initial state
    handleResize();
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [dispatch]);

  // Actions
  const handleNewChat = useCallback(() => {
    const sessionId = crypto.randomUUID();
    const sessionName = `Chat ${allSessions.length + 1}`;

    dispatch(createSession({ id: sessionId, name: sessionName, owner: user.userId || '', config: {
      domainId: 'general',
      personaId: 'default',
      isMemoryEnabled: true,
      isResearchMode: false,
    } }));

    // Close sidebar on mobile
    if (typeof window !== 'undefined' && window.innerWidth < 768 && isSidebarOpen) {
      dispatch(toggleSidebar());
    }

    return sessionId;
  }, [dispatch, allSessions.length, isSidebarOpen, user.userId]);

  const handleSelectChat = useCallback((chatId: string) => {
    dispatch(selectSession(chatId));

    // Close sidebar on mobile
    if (typeof window !== 'undefined' && window.innerWidth < 768 && isSidebarOpen) {
      dispatch(toggleSidebar());
    }
  }, [dispatch, isSidebarOpen]);

  const handleDeleteChat = useCallback((chatId: string) => {
    dispatch(deleteSession(chatId));
  }, [dispatch]);

  const handleRenameChat = useCallback((chatId: string, newName: string) => {
    dispatch(renameSession({ id: chatId, name: newName }));
  }, [dispatch]);

  const handleSendMessage = useCallback(async (content: string) => {
    if (!currentSession) {
      // Create new session if needed
      const sessionId = handleNewChat();

      // Add user message
      const userMessage = {
        id: crypto.randomUUID(),
        role: 'user' as const,
        content,
        timestamp: Date.now(),
      };

      dispatch(addMessage({ sessionId, message: userMessage }));

      // Send message
      await dispatch(sendMessage({
        sessionId,
        message: content,
        modelId: sessionConfig?.modelId || 'deepseek-r1',
        domainId: sessionConfig?.domainId,
        persona: sessionConfig?.personaId,
      }));
    } else {
      // Add user message to existing session
      const userMessage = {
        id: crypto.randomUUID(),
        role: 'user' as const,
        content,
        timestamp: Date.now(),
      };

      dispatch(addMessage({ sessionId: currentSession.id, message: userMessage }));

      // Send message
      await dispatch(sendMessage({
        sessionId: currentSession.id,
        message: content,
        modelId: currentSession.config.modelId,
        domainId: currentSession.config.domainId,
        persona: currentSession.config.personaId,
      }));
    }
  }, [currentSession, sessionConfig, dispatch, handleNewChat]);

  const handleToggleSidebar = useCallback(() => {
    dispatch(toggleSidebar());
  }, [dispatch]);

  const handleToggleResearch = useCallback(() => {
    if (supportsResearch && currentSession) {
      dispatch(toggleSessionResearch({ sessionId: currentSession.id }));
    }
  }, [dispatch, supportsResearch, currentSession]);

  return {
    // State
    currentSession,
    allSessions,
    isSidebarOpen,
    isResearchMode: sessionResearchMode,
    user,
    sessionConfig,
    isMemoryEnabled,
    supportsResearch,

    // Actions
    handleNewChat,
    handleSelectChat,
    handleDeleteChat,
    handleRenameChat,
    handleSendMessage,
    handleToggleSidebar,
    handleToggleResearch,
    
    // Session config actions
    updateSessionConfig: (config: any) => currentSession && dispatch(updateSessionConfig({ sessionId: currentSession.id, config })),
    setSessionModel: (modelId: string) => currentSession && dispatch(setSessionModel({ sessionId: currentSession.id, modelId })),
    setSessionDomain: (domainId?: string) => currentSession && dispatch(setSessionDomain({ sessionId: currentSession.id, domainId })),
    setSessionPersona: (personaId?: string) => currentSession && dispatch(setSessionPersona({ sessionId: currentSession.id, personaId })),
    toggleSessionMemory: () => currentSession && dispatch(toggleSessionMemory({ sessionId: currentSession.id })),
  };
}