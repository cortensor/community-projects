"use client"

import { Brain, Zap, ChevronUp, ChevronDown, Eye, EyeOff } from "lucide-react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useState } from "react"

interface DeepThinkingToggleProps {
  enabled: boolean
  onToggle: (enabled: boolean) => void
  disabled?: boolean
  modelId: string
  className?: string
  collapsible?: boolean
}

export function DeepThinkingToggle({ 
  enabled, 
  onToggle, 
  disabled = false, 
  modelId,
  className,
  collapsible = true
}: DeepThinkingToggleProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const isDeepseek = modelId === 'deepseek-r1'
  
  // Only show toggle for Deepseek R1, default model always uses basic deep thinking
  if (!isDeepseek) {
    return null
  }

  // Compact view when collapsed
  if (collapsible && isCollapsed) {
    return (
      <div className={cn("flex items-center justify-between p-1.5 bg-card/40 backdrop-blur-sm rounded border border-border/30 transition-all duration-200", className)}>
        <div className="flex items-center gap-1.5">
          <div className={cn(
            "w-5 h-5 rounded-full flex items-center justify-center transition-all duration-200",
            enabled 
              ? "bg-gradient-to-r from-purple-500 to-blue-500 text-white" 
              : "bg-muted text-muted-foreground"
          )}>
            {enabled ? <Brain className="h-2.5 w-2.5" /> : <Zap className="h-2.5 w-2.5" />}
          </div>
          
          <Switch
            id="deep-thinking-toggle-compact"
            checked={enabled}
            onCheckedChange={onToggle}
            disabled={disabled}
            className={cn(
              "scale-75 data-[state=checked]:bg-gradient-to-r data-[state=checked]:from-purple-500 data-[state=checked]:to-blue-500",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          />
        </div>
        
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsCollapsed(false)}
          className="h-5 w-5 p-0 text-muted-foreground hover:text-foreground"
          disabled={disabled}
        >
          <ChevronDown className="h-2.5 w-2.5" />
        </Button>
      </div>
    )
  }

  // Full view
  return (
    <div className={cn("flex items-center gap-2 p-2 bg-card/60 backdrop-blur-sm rounded border border-border/50 transition-all duration-200", className)}>
      <div className="flex items-center gap-2 flex-1">
        <div className={cn(
          "w-6 h-6 rounded-full flex items-center justify-center transition-all duration-200",
          enabled 
            ? "bg-gradient-to-r from-purple-500 to-blue-500 text-white" 
            : "bg-muted text-muted-foreground"
        )}>
          {enabled ? <Brain className="h-3 w-3" /> : <Zap className="h-3 w-3" />}
        </div>
        
        <div className="flex-1">
          <Label 
            htmlFor="deep-thinking-toggle" 
            className={cn(
              "text-xs font-medium cursor-pointer transition-colors",
              enabled ? "text-purple-700 dark:text-purple-300" : "text-foreground"
            )}
          >
            Deep Thinking
          </Label>
          <div className="text-xs text-muted-foreground">
            {enabled ? "Enhanced reasoning" : "Quick responses"}
          </div>
        </div>

        <div className="flex items-center gap-1">
          {enabled && (
            <Badge variant="secondary" className="text-xs bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 px-1 py-0 h-4">
              🧠
            </Badge>
          )}
          
          <Switch
            id="deep-thinking-toggle"
            checked={enabled}
            onCheckedChange={onToggle}
            disabled={disabled}
            className={cn(
              "scale-75 data-[state=checked]:bg-gradient-to-r data-[state=checked]:from-purple-500 data-[state=checked]:to-blue-500",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          />
          
          {collapsible && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsCollapsed(true)}
              className="h-5 w-5 p-0 text-muted-foreground hover:text-foreground"
              disabled={disabled}
            >
              <ChevronUp className="h-2.5 w-2.5" />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
