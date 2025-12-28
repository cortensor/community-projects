'use client'

import { useState, useCallback, useMemo } from 'react'
import { useAccount, usePublicClient } from 'wagmi'
import { toast } from 'sonner'
import {
  useReadSessionQueueV2GetTasksBySessionId,
  useReadSessionQueueV2GetAllTaskResults,
  useWriteSessionV2Submit
} from '@/generated'
import { useCurrentSessionId } from '../store/useSessionStore'
import { DEFAULT_TASK_CONFIG, SYSTEM_INSTRUCTIONS, CHAT_HISTORY_CONFIG } from '@/lib/constants'

export interface TaskData {
  sessionId: number
  taskId: number
  globalId?: number
  content: string
  status: 'submitting' | 'queued' | 'assigned' | 'completed' | 'failed'
  timestamp: Date
  transactionHash?: string
  assignedMiners?: string[]
  results?: string[]
  resultMiners?: string[]
}

export interface ChatMessage {
  id: string
  content: string
  sender: 'user' | 'ai'
  timestamp: Date
  taskId?: number
  sessionId?: number
}

export interface UseTasksReturn {
  // State
  tasks: TaskData[]
  messages: ChatMessage[]
  isSubmittingTask: boolean

  // Actions
  submitTask: (sessionId: number, message: string) => Promise<void>
  getTaskResults: (sessionId: number, taskId: number) => Promise<void>
  clearMessages: () => void
  
  // Utility
  formatChatHistory: (currentMessages: ChatMessage[], newUserMessage: string) => string
}

export function useCortensorTasks(): UseTasksReturn {
  const { address } = useAccount()
  const publicClient = usePublicClient()
  const currentSessionId = useCurrentSessionId()
  // Task submission hook
  const { writeContractAsync: submitTaskContract, isPending: isSubmittingTask } = useWriteSessionV2Submit()

  // Bulk task results hook - gets all results for the current session
  //@ts-ignore  
  const { data: allTaskResults, refetch: refetchAllTaskResults } = useReadSessionQueueV2GetAllTaskResults({
    args: currentSessionId ? [BigInt(currentSessionId)] : undefined,
    query: {
      enabled: !!address && !!currentSessionId,
      refetchInterval: 5000, // Poll every 5 seconds for new results
    }
  })

  // Query tasks for the current session
  //@ts-ignore this is it 
  const { data: tasksData, refetch: refetchTasks } = useReadSessionQueueV2GetTasksBySessionId({
    args: currentSessionId ? [BigInt(currentSessionId)] : undefined,
    query: {
      enabled: !!address && !!currentSessionId,
      refetchInterval: 5000,
    }
  })

  // Helper function to convert blockchain status to our status type
  const convertStatus = (blockchainStatus: number): TaskData['status'] => {
    console.log("this is the blockchain status number at the moment", blockchainStatus);
    switch (blockchainStatus) {
      case 0: return 'queued'
      case 1: return 'assigned'
      case 2: return 'completed'
      case 3: return 'completed'
      case 4: return 'completed'
      default: return 'failed'
    }
  }

  // Process tasks data and include results from bulk query
  const tasks: TaskData[] = tasksData ? tasksData.map((task, taskIndex) => {
    // Extract original user message from contextual data if it exists
    let displayContent = task.data
    if (task.data.includes('Current user message: ')) {
      const parts = task.data.split('Current user message: ')
      displayContent = parts[parts.length - 1] || task.data
    }

    const taskData: TaskData = {
      sessionId: Number(task.sessionId),
      taskId: Number(task.id),
      globalId: Number(task.gid),
      content: displayContent, // Use extracted original message for display
      status: convertStatus(task.status),
      timestamp: new Date(Number(task.createdAt) * 1000),
      transactionHash: undefined, // Not available in this data structure
      assignedMiners: task.assignedMiners.map(addr => addr as string),
      results: undefined,
      resultMiners: undefined
    }

    // Include results from bulk query if available
    if (allTaskResults && allTaskResults.length >= 2) {
      const [resultMiners, resultData] = allTaskResults

      // Check if we have results for this task (by index)
      if (resultMiners[taskIndex] && resultData[taskIndex]) {
        const taskResultMiners = resultMiners[taskIndex] as string[]
        const taskResultData = resultData[taskIndex] as string[]

        if (taskResultData && taskResultData.length > 0) {
          console.log('Including bulk results for task:', taskData.taskId, {
            miners: taskResultMiners,
            results: taskResultData
          })

          taskData.results = taskResultData.filter(result => result && result.trim())
          taskData.resultMiners = taskResultMiners
        }
      }
    }

    return taskData
  }) : []





  // Note: Removed event listener - we now use polling via bulk query to get results

  // Helper function to format chat history for AI context
  const formatChatHistory = useCallback((currentMessages: ChatMessage[], newUserMessage: string): string => {
    // Get the last N messages (excluding the current one being submitted)
    const recentMessages = currentMessages
      .slice(-CHAT_HISTORY_CONFIG.maxHistoryMessages)
      .map(msg => `${msg.sender === 'user' ? 'User' : 'Assistant'}: ${msg.content}`)
      .join('\n')

    // Format the complete context with system instructions
    let context = ''
    
    if (CHAT_HISTORY_CONFIG.includeSystemInstructions) {
      context += `System Instructions: ${SYSTEM_INSTRUCTIONS}\n\n`
    }
    
    if (recentMessages) {
      context += `Previous conversation:\n${recentMessages}\n\n`
    }
    
    context += `Current user message: ${newUserMessage}`
    
    return context
  }, [])

  // Convert tasks to chat messages using useMemo to prevent infinite re-renders
  const messages = useMemo(() => {
    const chatMessages: ChatMessage[] = []

    tasks.forEach(task => {
      // Add user message
      chatMessages.push({
        id: `user-${task.sessionId}-${task.taskId}`,
        content: task.content,
        sender: 'user',
        timestamp: task.timestamp,
        taskId: task.taskId,
        sessionId: task.sessionId
      })

      // Add AI response if available (including empty strings)
      if (task.results && task.results.length > 0) {
        // Select the best result from multiple miners
        // Priority: first non-empty result, or first result if all are empty
        let aiResponse = task.results[0] // Default to first result

        // Try to find the first non-empty result
        for (const result of task.results) {
          if (result && result.trim()) {
            aiResponse = result
            break
          }
        }

        // Render the selected result (even if empty string)
        chatMessages.push({
          id: `ai-${task.sessionId}-${task.taskId}`,
          content: aiResponse || '', // Handle null/undefined as empty string
          sender: 'ai',
          timestamp: new Date(task.timestamp.getTime() + 1000), // Slightly after user message
          taskId: task.taskId,
          sessionId: task.sessionId
        })
      } else if (task.status === 'assigned') {
        // Show processing message
        chatMessages.push({
          id: `ai-processing-${task.sessionId}-${task.taskId}`,
          content: `Processing your request... (Assigned to ${task.assignedMiners?.length || 3} miners)`,
          sender: 'ai',
          timestamp: new Date(task.timestamp.getTime() + 500),
          taskId: task.taskId,
          sessionId: task.sessionId
        })
      }
    })

    // Sort messages by timestamp
    return chatMessages.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
  }, [tasks])

  const submitTask = async (sessionId: number, message: string) => {
    if (!address || !publicClient) {
      toast.error('Please connect your wallet first')
      return
    }

    // Format the message with chat history and system instructions
    const contextualMessage = formatChatHistory(messages, message)

    // Create task data object
    const taskData = {
      type: 'chat',
      message: contextualMessage
    }

    try {
      console.log('Submitting task with data:', {
        sessionId,
        originalMessage: message,
        contextualMessage,
        taskData,
        address
      })

      const txHash = await toast.promise(
        submitTaskContract({
          args: [
            BigInt(sessionId), // sessionId
            BigInt(0), // nodeType (0: ephemeral, 1: hybrid, 2: dedicated)
            contextualMessage, // taskData with history and system instructions
            BigInt(0), // promptType (0: default - eliza bot, 1: raw, 2: system template & input)
            '', // promptTemplate
            [
              BigInt(128), // maxTokens
              BigInt(70),  // temperature (scaled by 100, so this is 0.7)
              BigInt(100), // topP (scaled by 100, so this is 1.0)
              BigInt(40),  // topK
              BigInt(100), // repeatPenalty (scaled by 100, so this is 1.0)
              BigInt(0),   // presencePenalty
              BigInt(0)    // frequencyPenalty
            ], // llmParams
            'web-dashboard-cortensor' // clientReference
          ]
        }),
        {
          loading: 'Submitting task...',
          success: 'Task submitted successfully!',
          error: (error: any) => `Failed to submit task: ${error.message || 'Unknown error'}`
        }
      ).unwrap();

      // Wait for transaction confirmation - don't use toast.promise for receipt
      console.log('Waiting for transaction confirmation...')
      const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash })

      console.log('Transaction receipt received:', {
        hash: receipt.transactionHash,
        blockNumber: receipt.blockNumber,
        status: receipt.status,
        gasUsed: receipt.gasUsed,
        effectiveGasPrice: receipt.effectiveGasPrice,
        logs: receipt.logs
      })

      // Check if transaction was successful or reverted
      if (receipt.status === 'success') {
        console.log('Transaction successful - task submitted to blockchain')
        toast.success('Task successfully submitted and confirmed!')
      } else if (receipt.status === 'reverted') {
        console.error('Transaction reverted:', {
          hash: receipt.transactionHash,
          blockNumber: receipt.blockNumber,
          status: receipt.status,
          gasUsed: receipt.gasUsed
        })
        toast.error('Transaction was reverted by the smart contract')
        throw new Error(`Transaction reverted: ${receipt.transactionHash}`)
      } else {
        console.error('Transaction failed with unknown status:', {
          hash: receipt.transactionHash,
          status: receipt.status
        })
        toast.error('Transaction failed with unknown status')
        throw new Error(`Transaction failed with status: ${receipt.status}`)
      }

      refetchTasks()
    } catch (error: any) {
      console.error('Failed to submit task:', {
        error: error.message || error,
        stack: error.stack,
        sessionId,
        message,
        address
      })

      // Show user-friendly error message
      if (error.message?.includes('User rejected')) {
        toast.error('Transaction was rejected by user')
      } else if (error.message?.includes('insufficient funds')) {
        toast.error('Insufficient funds for transaction')
      } else if (error.message?.includes('reverted')) {
        toast.error('Transaction was reverted by the smart contract')
      } else {
        toast.error(`Failed to submit task: ${error.message || 'Unknown error'}`)
      }

      throw error
    }
  }

  // Simplified getTaskResults function - now just triggers a refetch of all results
  const getTaskResults = async (sessionId: number, taskId: number) => {
    try {
      console.log(`Refreshing results for session ${sessionId}, task ${taskId}`)
      await refetchAllTaskResults()
      console.log('All task results refreshed successfully')
    } catch (error: any) {
      console.error('Failed to refresh task results:', {
        error: error.message || error,
        stack: error.stack,
        sessionId,
        taskId
      })
      toast.error(`Failed to refresh results: ${error.message || 'Unknown error'}`)
      throw error
    }
  }

  const clearMessages = () => {
    refetchTasks()
  }

  return {
    tasks,
    messages,
    isSubmittingTask,
    submitTask,
    getTaskResults,
    clearMessages,
    formatChatHistory
  }
}