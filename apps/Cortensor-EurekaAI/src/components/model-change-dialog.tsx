"use client"

import React, { useEffect, useRef } from "react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Bot, Zap } from "lucide-react"

interface ModelChangeDialogProps {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  newModelName: string
  newModelId: string
  onConfirm: () => void
  onCancel: () => void
  isLoading?: boolean
}

const getModelIcon = (modelId: string) => {
  if (modelId === 'deepseek-r1') return <Zap className="h-4 w-4" />
  return <Bot className="h-4 w-4" />
}

export function ModelChangeDialog({
  isOpen,
  onOpenChange,
  newModelName,
  newModelId,
  onConfirm,
  onCancel,
  isLoading = false
}: ModelChangeDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  
  // Handle focus management and cleanup
  useEffect(() => {
    if (!isOpen && !isLoading) {
      // Clear any lingering focus issues after dialog closes
      setTimeout(() => {
        if (document.activeElement instanceof HTMLElement) {
          document.activeElement.blur()
        }
        // Focus back to body to prevent aria-hidden focus conflicts
        document.body.focus()
        
        // Remove any aria-hidden from body if present
        document.body.removeAttribute('aria-hidden')
      }, 100)
    }
  }, [isOpen, isLoading])
  
  const handleConfirm = () => {
    try {
      onConfirm()
    } catch (error) {
      console.error('Model change confirmation error:', error)
    }
  }
  
  const handleCancel = () => {
    try {
      onCancel()
    } catch (error) {
      console.error('Model change cancellation error:', error)
    }
  }
  
  const handleOpenChange = (open: boolean) => {
    if (!isLoading) {
      onOpenChange(open)
    }
  }

  return (
    <AlertDialog 
      open={isOpen} 
      onOpenChange={handleOpenChange}
    >
      <AlertDialogContent 
        className="sm:max-w-[425px]"
        onEscapeKeyDown={(e) => {
          // Prevent escape key when loading
          if (isLoading) {
            e.preventDefault()
          }
        }}
      >
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            {getModelIcon(newModelId)}
            Switch to {newModelName}?
          </AlertDialogTitle>
          <AlertDialogDescription>
            Changing the AI model will start a new chat session. Your current conversation will be saved.
            <br /><br />
            <strong>Would you like to continue?</strong>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel 
            ref={cancelRef}
            onClick={handleCancel} 
            disabled={isLoading}
            className="mr-2"
          >
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction 
            onClick={handleConfirm} 
            disabled={isLoading}
            className="min-w-[140px]"
          >
            {isLoading ? "Creating New Chat..." : "Start New Chat"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
