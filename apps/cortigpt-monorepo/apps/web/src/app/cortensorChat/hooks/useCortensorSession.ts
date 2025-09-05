'use client'

import { useEffect } from 'react'
import { useAccount, useReadContract, usePublicClient } from 'wagmi'
import {
  useWriteSessionV2Create,
  useReadSessionV2GetSessionsByAddress,
  useReadSessionV2GetSession,
  sessionV2Address,
  sessionV2Abi
} from '@/generated'
import { DEFAULT_SESSION_CONFIG } from '@/lib/constants'
import { useSessionStore, type SessionData } from '../store/useSessionStore'
import { toast } from 'sonner'

// TypeScript interface matching the blockchain Session struct
export interface BlockchainSession {
  id: bigint
  sid: `0x${string}`
  name: string
  metadata: string
  state: number // enum SessionState
  createdAt: bigint
  updatedAt: bigint
  owner: `0x${string}`
  ephemeralNodes: `0x${string}`[]
  dedicatedNodes: `0x${string}`[]
  mode: bigint
  redundant: bigint
  minNumOfNodes: bigint
  maxNumOfNodes: bigint
  numOfValidatorNodes: bigint
  routerMetadatas: string[]
  routerAddresses: `0x${string}`[]
  sla: bigint
  modelIdentifier: bigint
  reservePeriod: bigint
  maxTaskExecutionCount: bigint
}

export interface UseSessionReturn {
  // State
  currentSession: SessionData | null
  userSessions: SessionData[]
  isCreatingSession: boolean
  isLoadingSessions: boolean

  // Actions
  createSession: (name: string, metadata?: string) => Promise<void>
  selectSession: (sessionId: number) => void
  refreshSessions: () => void
}

export function useCortensorSession(): UseSessionReturn {
  const { address, isConnected } = useAccount()
  const publicClient = usePublicClient()
  const {
    currentSession,
    availableSessions,
    setCurrentSession,
    setAvailableSessions
  } = useSessionStore()

  // Get user sessions from blockchain
  // @ts-expect-error - Generated hook may have type issues
  const { data: sessionsData, isLoading: isLoadingSessions, refetch: refetchSessions } = useReadSessionV2GetSessionsByAddress({
    args: address ? [address] : undefined,
    query: {
      enabled: !!address && isConnected,
      refetchInterval: 10000, // Refetch every 10 seconds
    }
  })

  // Session creation hook
  const { writeContractAsync: createSessionContract, isPending: isCreatingSession } = useWriteSessionV2Create()

  const getSession = async (sessionId: number): Promise<SessionData | null> => {
    try {
      const result = await publicClient?.readContract({
        address: sessionV2Address[421614],
        abi: sessionV2Abi,
        functionName: 'getSession',
        args: [BigInt(sessionId)],
      })

      if (result) {
        const session = result as BlockchainSession
        return transformSession(session)
      }
      return null
    } catch (error) {
      console.error('Error fetching session:', error)
      return null
    }
  }

  // Transform blockchain sessions to store format
  const transformSession = (session: BlockchainSession): SessionData => {
    return {
      sessionId: Number(session.id),
      name: session.name,
      metadata: session.metadata,
      owner: session.owner,
      minNumOfNodes: session.minNumOfNodes,
      maxNumOfNodes: session.maxNumOfNodes,
      redundant: session.redundant,
      numOfValidatorNodes: session.numOfValidatorNodes,
      mode: session.mode,
      reserveEphemeralNodes: false, // Default value
      isActive: session.state === 1, // Assuming 1 is active state
      createdAt: session.createdAt,
      sla: session.sla,
    }
  }

  // Process sessions data when it changes
  useEffect(() => {
    if (sessionsData && Array.isArray(sessionsData)) {
      const processedSessions: SessionData[] = sessionsData.map((session: BlockchainSession) => transformSession(session))

      setAvailableSessions(processedSessions)

      // Auto-select the most recent active session if none is selected
      if (!currentSession && processedSessions.length > 0) {
        const activeSession = processedSessions.find(s => s.isActive) || processedSessions[0]
        setCurrentSession(activeSession)
      }
    }
  }, [sessionsData, currentSession, setAvailableSessions, setCurrentSession])

  const createSession = async (name: string, metadata: string = '') => {
    if (!address || !isConnected || !publicClient) {
      toast.error('Please connect your wallet first')
      return
    }

    try {
      const txHash = await toast.promise(
        createSessionContract({
          args: [
            name,
            metadata,
            address, // variableAddress
            DEFAULT_SESSION_CONFIG.minNumOfNodes,
            DEFAULT_SESSION_CONFIG.maxNumOfNodes,
            DEFAULT_SESSION_CONFIG.redundant,
            DEFAULT_SESSION_CONFIG.numOfValidatorNodes,
            DEFAULT_SESSION_CONFIG.mode,
            DEFAULT_SESSION_CONFIG.reserveEphemeralNodes,
            DEFAULT_SESSION_CONFIG.sla,
            DEFAULT_SESSION_CONFIG.modelIdentifier,
            DEFAULT_SESSION_CONFIG.reservePeriod,
            DEFAULT_SESSION_CONFIG.maxTaskExecutionCount
          ]
        }),
        {
          loading: 'Creating session...',
          success: 'Session created successfully!',
          error: 'Failed to create session'
        }
      ).unwrap();

      // Wait for transaction confirmation
      await toast.promise(
        publicClient.waitForTransactionReceipt({ hash: txHash }),
        {
          loading: 'Waiting for confirmation...',
          success: 'Session confirmed on blockchain!',
          error: 'Transaction failed'
        }
      ).unwrap();

      refetchSessions()
    } catch (error: unknown) {
      console.error('Failed to create session:', error)
    }
  }

  const selectSession = (sessionId: number) => {
    const session = availableSessions.find(s => s.sessionId === sessionId)
    if (session) {
      setCurrentSession(session)
      toast.success(`Switched to session ${sessionId}`)
    }
  }

  const refreshSessions = () => {
    refetchSessions()
  }

  return {
    currentSession,
    userSessions: availableSessions,
    isCreatingSession,
    isLoadingSessions,
    createSession,
    selectSession,
    refreshSessions
  }
}