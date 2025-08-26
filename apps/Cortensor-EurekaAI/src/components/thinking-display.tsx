// src/components/thinking-display.tsx
"use client"

import React, { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronUp, Eye, EyeOff } from "lucide-react"

interface ThinkingDisplayProps {
  thinkingContent: string
  isVisible: boolean
}

export function ThinkingDisplay({ thinkingContent, isVisible }: ThinkingDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  if (!isVisible || !thinkingContent) {
    return null
  }

  return (
    <Card className="mb-4 bg-muted/30 border-l-4 border-l-primary">
      <div className="p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-lg">🤔</span>
            <span className="font-semibold text-sm text-muted-foreground">
              Thinking Process
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
          >
            {isExpanded ? (
              <EyeOff className="h-3 w-3" />
            ) : (
              <Eye className="h-3 w-3" />
            )}
          </Button>
        </div>
        {isExpanded && (
          <div className="text-sm text-muted-foreground thinking-content break-words overflow-wrap-anywhere whitespace-pre-wrap">
            {thinkingContent}
          </div>
        )}
        {!isExpanded && (
          <div className="text-xs text-muted-foreground/70 italic">
            Click the eye icon to view thinking process
          </div>
        )}
      </div>
    </Card>
  )
}
