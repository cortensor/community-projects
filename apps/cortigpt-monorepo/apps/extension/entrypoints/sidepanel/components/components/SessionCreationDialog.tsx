'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Loader2, Plus } from 'lucide-react'
import { useCortensorSession } from '../hooks/useCortensorSession'
import { useChatStore } from '../store/useChatStore'
import { DEFAULT_SESSION_CONFIG } from '@/lib/constants'

interface SessionCreationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SessionCreationDialog({ open, onOpenChange }: SessionCreationDialogProps) {
  const { createSession, isCreatingSession } = useCortensorSession()
  const { setSelectedSessionId } = useChatStore()
  
  const [sessionName, setSessionName] = useState('')
  const [sessionDescription, setSessionDescription] = useState('')
  
  const handleCreateSession = async () => {
    if (!sessionName.trim()) {
      return
    }
    
    try {
      await createSession(sessionName.trim(), sessionDescription.trim())
      
      // Session creation was successful
        onOpenChange(false)
        resetForm()
    } catch (error) {
      console.error('Failed to create session:', error)
    }
  }
  
  const resetForm = () => {
    setSessionName('')
    setSessionDescription('')
  }
  
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen && !isCreatingSession) {
      resetForm()
    }
    onOpenChange(newOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5" />
            Create New Session
          </DialogTitle>
          <DialogDescription>
            Create a new Cortensor session to start chatting with AI. Configure the session parameters below.
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="session-name">Session Name *</Label>
            <Input
              id="session-name"
              placeholder="Enter session name..."
              value={sessionName}
              onChange={(e) => setSessionName(e.target.value)}
              disabled={isCreatingSession}
            />
          </div>
          
          <div className="grid gap-2">
            <Label htmlFor="session-description">Description</Label>
            <Textarea
              id="session-description"
              placeholder="Optional description for this session..."
              value={sessionDescription}
              onChange={(e) => setSessionDescription(e.target.value)}
              disabled={isCreatingSession}
              rows={3}
            />
          </div>
          
          <div className="text-sm text-muted-foreground">
            Session will be created with default configuration:
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>Min Nodes: {DEFAULT_SESSION_CONFIG.minNumOfNodes.toString()}</li>
              <li>Max Nodes: {DEFAULT_SESSION_CONFIG.maxNumOfNodes.toString()}</li>
              <li>Redundancy: {DEFAULT_SESSION_CONFIG.redundant.toString()}x</li>
              <li>SLA: {DEFAULT_SESSION_CONFIG.sla.toString()}ms</li>
            </ul>
          </div>
        </div>
        
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isCreatingSession}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreateSession}
            disabled={!sessionName.trim() || isCreatingSession}
          >
            {isCreatingSession ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Session'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}