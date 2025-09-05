import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

// Utility function to safely extract hostname from URL
const safeGetHostname = (url: string): string => {
  if (!url || typeof url !== 'string') {
    return 'unknown page'
  }
  
  try {
    // First check if it looks like a URL
    if (!url.includes('://') && !url.startsWith('//')) {
      return 'unknown page'
    }
    
    const urlObj = new URL(url)
    return urlObj.hostname || 'unknown page'
  } catch {
    return 'unknown page'
  }
}

export interface ChatMessage {
  id: string
  content: string
  sender: 'user' | 'ai'
  timestamp: Date
}

export interface ChatHistoryItem {
  id: string
  title: string
  lastMessage: string
  timestamp: Date
  messageCount: number
}

export interface TabChatData {
  messages: ChatMessage[]
  chatHistory: ChatHistoryItem[]
  selectedChatId: string | null
  url: string
  hostname: string
}

interface ChatStore {
  // Per-tab chat data
  tabChats: Record<string, TabChatData>
  currentTabId: string | null

  // Actions
  setCurrentTab: (tabId: string, url: string) => void
  getCurrentTabData: () => TabChatData | null

  // Chat management
  createNewChat: (tabId: string) => string
  setSelectedChat: (tabId: string, chatId: string) => void

  // Message management
  addMessage: (tabId: string, chatId: string, message: ChatMessage) => void
  setMessages: (tabId: string, chatId: string, messages: ChatMessage[]) => void
  getMessages: (tabId: string, chatId: string) => ChatMessage[]

  // Chat history management
  updateChatHistory: (tabId: string, chatId: string, lastMessage: string, messageCount: number) => void
  getChatHistory: (tabId: string) => ChatHistoryItem[]

  // Utility functions
  clearTabData: (tabId: string) => void
  getTabUrl: (tabId: string) => string | null
}

const createInitialTabData = (url: string): TabChatData => {
  const hostname = safeGetHostname(url)
  return {
    messages: [],
    chatHistory: [],
    selectedChatId: null,
    url,
    hostname
  }
}

const generateChatId = (): string => {
  return `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

const generateMessageId = (): string => {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      tabChats: {},
      currentTabId: null,

      setCurrentTab: (tabId: string, url: string) => {
        set((state: ChatStore) => {
          const newState = { ...state, currentTabId: tabId }

          // Initialize tab data if it doesn't exist
          if (!newState.tabChats[tabId]) {
            newState.tabChats[tabId] = createInitialTabData(url)
          } else {
            // Update URL if it has changed
            newState.tabChats[tabId].url = url
            newState.tabChats[tabId].hostname = safeGetHostname(url)
          }

          return newState
        })
      },

      getCurrentTabData: () => {
        const { currentTabId, tabChats } = get() as ChatStore
        return currentTabId ? tabChats[currentTabId] || null : null
      },

      createNewChat: (tabId: string) => {
        const chatId = generateChatId()

        set((state: ChatStore) => {
          const tabData = state.tabChats[tabId]
          if (!tabData) return state

          const newChat: ChatHistoryItem = {
            id: chatId,
            title: `Chat ${tabData.chatHistory.length + 1}`,
            lastMessage: 'New conversation started',
            timestamp: new Date(),
            messageCount: 0
          }

          return {
            ...state,
            tabChats: {
              ...state.tabChats,
              [tabId]: {
                ...tabData,
                chatHistory: [newChat, ...tabData.chatHistory],
                selectedChatId: chatId
              }
            }
          }
        })

        return chatId
      },

      setSelectedChat: (tabId: string, chatId: string) => {
        set((state: ChatStore) => {
          const tabData = state.tabChats[tabId]
          if (!tabData) return state

          return {
            ...state,
            tabChats: {
              ...state.tabChats,
              [tabId]: {
                ...tabData,
                selectedChatId: chatId
              }
            }
          }
        })
      },

      addMessage: (tabId: string, chatId: string, message: ChatMessage) => {
        set((state: ChatStore) => {
          const tabData = state.tabChats[tabId]
          if (!tabData) return state

          const chatKey = `${tabId}_${chatId}`
          const existingMessages = (get() as ChatStore).getMessages(tabId, chatId)

          return {
            ...state,
            tabChats: {
              ...state.tabChats,
              [tabId]: {
                ...tabData,
                messages: [...existingMessages, message]
              }
            }
          }
        })
      },

      setMessages: (tabId: string, chatId: string, messages: ChatMessage[]) => {
        set((state: ChatStore) => {
          const tabData = state.tabChats[tabId]
          if (!tabData) return state

          return {
            ...state,
            tabChats: {
              ...state.tabChats,
              [tabId]: {
                ...tabData,
                messages
              }
            }
          }
        })
      },

      getMessages: (tabId: string, chatId: string) => {
        const { tabChats } = get() as ChatStore
        const tabData = tabChats[tabId]
        if (!tabData || !tabData.selectedChatId || tabData.selectedChatId !== chatId) {
          return []
        }
        return tabData.messages || []
      },

      updateChatHistory: (tabId: string, chatId: string, lastMessage: string, messageCount: number) => {
        set((state: ChatStore) => {
          const tabData = state.tabChats[tabId]
          if (!tabData) return state

          const updatedHistory = tabData.chatHistory.map(chat =>
            chat.id === chatId
              ? {
                ...chat,
                lastMessage,
                timestamp: new Date(),
                messageCount
              }
              : chat
          )

          return {
            ...state,
            tabChats: {
              ...state.tabChats,
              [tabId]: {
                ...tabData,
                chatHistory: updatedHistory
              }
            }
          }
        })
      },

      getChatHistory: (tabId: string) => {
        const { tabChats } = get() as ChatStore
        const tabData = tabChats[tabId]
        return tabData ? tabData.chatHistory : []
      },

      clearTabData: (tabId: string) => {
        set((state: ChatStore) => {
          const newTabChats = { ...state.tabChats }
          delete newTabChats[tabId]

          return {
            ...state,
            tabChats: newTabChats,
            currentTabId: state.currentTabId === tabId ? null : state.currentTabId
          }
        })
      },

      getTabUrl: (tabId: string) => {
        const { tabChats } = get() as ChatStore
        const tabData = tabChats[tabId]
        return tabData ? tabData.url : null
      }
    }),
    {
      name: 'cortensor-chat-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state: ChatStore) => ({ tabChats: state.tabChats })
    }
  )
)

// Helper hook for current tab
export const useCurrentTabChat = () => {
  const store = useChatStore()
  const currentTabData = store.getCurrentTabData()

  return {
    ...currentTabData,
    ...store
  }
}