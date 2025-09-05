'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

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

interface Web2ChatStore {
  // Current state
  selectedChatId: string | null
  chatHistory: ChatHistoryItem[]
  messages: Record<string, ChatMessage[]> // chatId -> messages
  userAddress: string | null

  // Actions
  setUserAddress: (address: string) => void
  setSelectedChatId: (chatId: string | null) => void
  
  // Chat management
  createNewChat: () => string
  deleteChat: (chatId: string) => void
  switchToChat: (chatId: string) => void
  
  // Message management
  addMessage: (chatId: string, message: ChatMessage) => void
  setMessages: (chatId: string, messages: ChatMessage[]) => void
  getMessages: (chatId: string) => ChatMessage[]
  
  // Chat history management
  updateChatHistory: (chatId: string, lastMessage: string, messageCount: number) => void
  setChatHistory: (history: ChatHistoryItem[]) => void
  
  // Persistence
  loadUserData: (userAddress: string) => void
  saveToLocalStorage: () => void
  
  // Utility
  reset: () => void
}

const initialState = {
  selectedChatId: null,
  chatHistory: [],
  messages: {},
  userAddress: null,
}

export const useWeb2ChatStore = create<Web2ChatStore>()(
  persist(
    immer((set, get) => ({
      ...initialState,

      setUserAddress: (address: string) => {
        set((state) => {
          state.userAddress = address
        })
        // Load user-specific data when address is set
        get().loadUserData(address)
      },

      setSelectedChatId: (chatId: string | null) => {
        set((state) => {
          state.selectedChatId = chatId
        })
        
        // Save to localStorage
        if (get().userAddress && chatId) {
          localStorage.setItem(`cortensor_current_chat_${get().userAddress}`, chatId)
        } else if (get().userAddress) {
          localStorage.removeItem(`cortensor_current_chat_${get().userAddress}`)
        }
      },

      createNewChat: () => {
        const newChatId = `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        const currentHistory = get().chatHistory
        
        const newChat: ChatHistoryItem = {
          id: newChatId,
          title: `Chat ${currentHistory.length + 1}`,
          lastMessage: 'New conversation started',
          timestamp: new Date(),
          messageCount: 0
        }

        set((state) => {
          state.chatHistory = [newChat, ...state.chatHistory]
          state.selectedChatId = newChatId
          state.messages[newChatId] = []
        })

        get().saveToLocalStorage()
        return newChatId
      },

      deleteChat: (chatId: string) => {
        set((state) => {
          // Remove from chat history
          state.chatHistory = state.chatHistory.filter(chat => chat.id !== chatId)
          
          // Remove messages
          delete state.messages[chatId]
          
          // Clear selected chat if it's the deleted one
          if (state.selectedChatId === chatId) {
            state.selectedChatId = null
          }
        })

        // Remove from localStorage
        const userAddress = get().userAddress
        if (userAddress) {
          localStorage.removeItem(`cortensor_messages_${userAddress}_${chatId}`)
          if (get().selectedChatId === null) {
            localStorage.removeItem(`cortensor_current_chat_${userAddress}`)
          }
        }

        get().saveToLocalStorage()
      },

      switchToChat: (chatId: string) => {
        set((state) => {
          state.selectedChatId = chatId
        })
        
        const userAddress = get().userAddress
        if (userAddress) {
          localStorage.setItem(`cortensor_current_chat_${userAddress}`, chatId)
        }
      },

      addMessage: (chatId: string, message: ChatMessage) => {
        set((state) => {
          if (!state.messages[chatId]) {
            state.messages[chatId] = []
          }
          state.messages[chatId].push(message)
        })

        // Save messages to localStorage
        const userAddress = get().userAddress
        if (userAddress) {
          const messages = get().messages[chatId] || []
          localStorage.setItem(`cortensor_messages_${userAddress}_${chatId}`, JSON.stringify(messages))
        }
      },

      setMessages: (chatId: string, messages: ChatMessage[]) => {
        set((state) => {
          state.messages[chatId] = messages
        })

        // Save messages to localStorage
        const userAddress = get().userAddress
        if (userAddress) {
          localStorage.setItem(`cortensor_messages_${userAddress}_${chatId}`, JSON.stringify(messages))
        }
      },

      getMessages: (chatId: string) => {
        return get().messages[chatId] || []
      },

      updateChatHistory: (chatId: string, lastMessage: string, messageCount: number) => {
        set((state) => {
          const chatIndex = state.chatHistory.findIndex(chat => chat.id === chatId)
          if (chatIndex !== -1) {
            state.chatHistory[chatIndex] = {
              ...state.chatHistory[chatIndex],
              lastMessage,
              timestamp: new Date(),
              messageCount
            }
          }
        })

        get().saveToLocalStorage()
      },

      setChatHistory: (history: ChatHistoryItem[]) => {
        set((state) => {
          state.chatHistory = history
        })
      },

      loadUserData: (userAddress: string) => {
        // Load chat history
        const savedHistory = localStorage.getItem(`cortensor_chat_history_${userAddress}`)
        if (savedHistory) {
          try {
            const parsed = JSON.parse(savedHistory) as Array<{
              id: string
              title: string
              lastMessage: string
              timestamp: string
              messageCount: number
            }>
            const history = parsed.map((item) => ({
              ...item,
              timestamp: new Date(item.timestamp)
            }))
            
            set((state) => {
              state.chatHistory = history
            })
          } catch (error) {
            console.error('Failed to parse chat history:', error)
          }
        }

        // Load current selected chat
        const currentChatId = localStorage.getItem(`cortensor_current_chat_${userAddress}`)
        if (currentChatId) {
          set((state) => {
            state.selectedChatId = currentChatId
          })

          // Load messages for the current chat
          const savedMessages = localStorage.getItem(`cortensor_messages_${userAddress}_${currentChatId}`)
          if (savedMessages) {
            try {
              const parsed = JSON.parse(savedMessages) as Array<{
                id: string
                content: string
                sender: 'user' | 'ai'
                timestamp: string
              }>
              const messages = parsed.map((msg) => ({
                ...msg,
                timestamp: new Date(msg.timestamp)
              }))
              
              set((state) => {
                state.messages[currentChatId] = messages
              })
            } catch (error) {
              console.error('Failed to parse messages:', error)
            }
          }
        }
      },

      saveToLocalStorage: () => {
        const { userAddress, chatHistory } = get()
        if (userAddress) {
          localStorage.setItem(`cortensor_chat_history_${userAddress}`, JSON.stringify(chatHistory))
        }
      },

      reset: () => {
        set((state) => {
          Object.assign(state, initialState)
        })
      },
    })),
    {
      name: 'cortensor-web2-chat-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state: Web2ChatStore) => ({
        selectedChatId: state.selectedChatId,
        chatHistory: state.chatHistory,
        messages: state.messages,
        userAddress: state.userAddress,
      }),
    }
  )
)

// Helper hook for easier usage
export const useWeb2Chat = () => {
  const store = useWeb2ChatStore()
  
  return {
    // State
    currentMessages: store.selectedChatId ? store.getMessages(store.selectedChatId) : [],
    
    // Actions and other state (spread includes selectedChatId, chatHistory, userAddress)
    ...store,
  }
}