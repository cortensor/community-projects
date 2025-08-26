"use client"

import { Eye, EyeOff, Brain, Code } from "lucide-react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface ThinkingProcessToggleProps {
  enabled: boolean
  onToggle: (enabled: boolean) => void
  disabled?: boolean
  modelId: string
  className?: string
}

export function ThinkingProcessToggle({ 
  enabled, 
  onToggle, 
  disabled = false, 
  modelId,
  className 
}: ThinkingProcessToggleProps) {
  // Only show for DeepSeek R1 model
  const isDeepseek = modelId === 'deepseek-r1'
  
  if (!isDeepseek) {
    return null
  }

  const handleToggle = (checked: boolean) => {
    console.log('Thinking Process Toggle changed:', { from: enabled, to: checked, model: modelId });
    onToggle(checked);
  };

  return (
    <div className={cn("flex items-center gap-3 p-3 bg-card/60 backdrop-blur-sm rounded-lg border border-border/50", className)}>
      <div className="flex items-center gap-2 flex-1">
        <div className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200",
          enabled 
            ? "bg-gradient-to-r from-indigo-500 to-purple-500 text-white" 
            : "bg-muted text-muted-foreground"
        )}>
          {enabled ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
        </div>
        
        <div className="flex-1">
          <Label 
            htmlFor="thinking-process-toggle" 
            className="text-sm font-medium cursor-pointer flex items-center gap-2"
          >
            <span>Thinking Process</span>
            <Badge 
              variant="secondary" 
              className={cn(
                "text-xs px-2 py-0.5 transition-colors",
                enabled 
                  ? "bg-indigo-500/20 text-indigo-600 border-indigo-500/30" 
                  : "bg-muted text-muted-foreground"
              )}
            >
              <Brain className="h-3 w-3 mr-1" />
              Built-in
            </Badge>
          </Label>
          <p className="text-xs text-muted-foreground mt-0.5">
            {enabled 
              ? "Showing AI reasoning process like ChatGPT o1" 
              : "Clean output without reasoning process"
            }
          </p>
        </div>
      </div>
      
      <Switch
        id="thinking-process-toggle"
        checked={enabled}
        onCheckedChange={handleToggle}
        disabled={disabled}
        className="data-[state=checked]:bg-indigo-600"
      />
    </div>
  )
}
