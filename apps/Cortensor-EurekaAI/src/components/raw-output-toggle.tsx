"use client"

import { Code, FileText } from "lucide-react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface RawOutputToggleProps {
  enabled: boolean
  onToggle: (enabled: boolean) => void
  disabled?: boolean
  className?: string
}

export function RawOutputToggle({ 
  enabled, 
  onToggle, 
  disabled = false, 
  className 
}: RawOutputToggleProps) {
  const handleToggle = (checked: boolean) => {
    console.log('RAW Output Toggle changed:', { from: enabled, to: checked });
    onToggle(checked);
  };

  return (
    <div className={cn("flex items-center gap-3 p-3 bg-card/60 backdrop-blur-sm rounded-lg border border-border/50", className)}>
      <div className="flex items-center gap-2 flex-1">
        <div className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200",
          enabled 
            ? "bg-gradient-to-r from-emerald-500 to-teal-500 text-white" 
            : "bg-muted text-muted-foreground"
        )}>
          {enabled ? <Code className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
        </div>
        
        <div className="flex-1">
          <Label 
            htmlFor="raw-output-toggle" 
            className={cn(
              "text-sm font-medium cursor-pointer transition-colors",
              enabled ? "text-emerald-700 dark:text-emerald-300" : "text-foreground"
            )}
          >
            RAW JSON Output
          </Label>
          <div className="text-xs text-muted-foreground mt-0.5">
            {enabled 
              ? "Show original JSON structure from Cortensor API (text, raw, etc.)"
              : "Get processed text responses (default)"
            }
          </div>
        </div>

        <div className="flex items-center gap-2">
          {enabled && (
            <Badge variant="secondary" className="text-xs bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300">
              🔧 RAW
            </Badge>
          )}
          
          <Switch
            id="raw-output-toggle"
            checked={enabled}
            onCheckedChange={handleToggle}
            disabled={disabled}
            className={cn(
              "data-[state=checked]:bg-gradient-to-r data-[state=checked]:from-emerald-500 data-[state=checked]:to-teal-500",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          />
        </div>
      </div>
    </div>
  )
}
