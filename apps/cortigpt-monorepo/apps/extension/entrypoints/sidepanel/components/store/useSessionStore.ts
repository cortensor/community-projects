'use client'

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export interface SessionData {
  sessionId: number
  name: string
  metadata: string
  owner: string
  minNumOfNodes: bigint
  maxNumOfNodes: bigint
  redundant: bigint
  numOfValidatorNodes: bigint
  mode: bigint
  reserveEphemeralNodes: boolean
  isActive: boolean
  createdAt: bigint
  nodeCount?: number
  sla?: bigint
  timestamp?: bigint
  description?: string
}

interface SessionStore {
  // State
  currentSession: SessionData | null
  availableSessions: SessionData[]
  isSessionDialogOpen: boolean

  // Actions
  setCurrentSession: (session: SessionData | null) => void
  addSession: (session: SessionData) => void
  updateSession: (sessionId: number, updates: Partial<SessionData>) => void
  removeSession: (sessionId: number) => void
  setAvailableSessions: (sessions: SessionData[]) => void
  setSessionDialogOpen: (open: boolean) => void
  clearSessions: () => void

  // Getters
  getCurrentSessionId: () => number | null
  getSessionById: (sessionId: number) => SessionData | null
}

export const useSessionStore = create<SessionStore>()(devtools(
  (set, get) => ({
    // Initial state
    currentSession: null,
    availableSessions: [],
    isSessionDialogOpen: false,

    // Actions
    setCurrentSession: (session) => {
      set({ currentSession: session }, false, 'setCurrentSession')
    },

    addSession: (session) => {
      set((state) => ({
        availableSessions: [...state.availableSessions, session]
      }), false, 'addSession')
    },

    updateSession: (sessionId, updates) => {
      set((state) => ({
        availableSessions: state.availableSessions.map(session =>
          session.sessionId === sessionId
            ? { ...session, ...updates }
            : session
        ),
        currentSession: state.currentSession?.sessionId === sessionId
          ? { ...state.currentSession, ...updates }
          : state.currentSession
      }), false, 'updateSession')
    },

    removeSession: (sessionId) => {
      set((state) => ({
        availableSessions: state.availableSessions.filter(
          session => session.sessionId !== sessionId
        ),
        currentSession: state.currentSession?.sessionId === sessionId
          ? null
          : state.currentSession
      }), false, 'removeSession')
    },

    setAvailableSessions: (sessions) => {
      set({ availableSessions: sessions }, false, 'setAvailableSessions')
    },

    setSessionDialogOpen: (open) => {
      set({ isSessionDialogOpen: open }, false, 'setSessionDialogOpen')
    },

    clearSessions: () => {
      set({
        currentSession: null,
        availableSessions: [],
        isSessionDialogOpen: false
      }, false, 'clearSessions')
    },

    // Getters
    getCurrentSessionId: () => {
      return get().currentSession?.sessionId || null
    },

    getSessionById: (sessionId) => {
      return get().availableSessions.find(session => session.sessionId === sessionId) || null
    }
  }),
  {
    name: 'session-store'
  }
))

// Selector hooks for better performance
export const useCurrentSession = () => useSessionStore(state => state.currentSession)
export const useCurrentSessionId = () => useSessionStore(state => state.getCurrentSessionId())
export const useAvailableSessions = () => useSessionStore(state => state.availableSessions)
export const useSessionDialogOpen = () => useSessionStore(state => state.isSessionDialogOpen)