'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

interface ChatUIState {
  // UI State
  currentMessage: string
  isSessionDialogOpen: boolean
  selectedSessionId: number | null

  // Actions
  setCurrentMessage: (message: string) => void
  setSessionDialogOpen: (open: boolean) => void
  setSelectedSessionId: (sessionId: number | null) => void
  clearCurrentMessage: () => void
  reset: () => void
}

const initialState = {
  currentMessage: '',
  isSessionDialogOpen: false,
  selectedSessionId: null,
}

export const useChatStore = create<ChatUIState>()(
  persist(
    immer((set) => ({
      ...initialState,

      setCurrentMessage: (message: string) => set((state) => {
        state.currentMessage = message
      }),

      setSessionDialogOpen: (open: boolean) => set((state) => {
        state.isSessionDialogOpen = open
      }),

      setSelectedSessionId: (sessionId: number | null) => set((state) => {
        state.selectedSessionId = sessionId
      }),

      clearCurrentMessage: () => set((state) => {
        state.currentMessage = ''
      }),

      reset: () => set((state) => {
        Object.assign(state, initialState)
      }),
    })),
    {
      name: 'cortensor-chat-ui',
      storage: createJSONStorage(() => localStorage),
      partialize: (state: ChatUIState) => ({
        selectedSessionId: state.selectedSessionId,
      }),
    }
  )
)