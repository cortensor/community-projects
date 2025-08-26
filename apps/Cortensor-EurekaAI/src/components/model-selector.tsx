"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ChevronDown, Bot, Zap } from "lucide-react"
import { appConfig } from "@/lib/app-config"
import { cn } from "@/lib/utils"

import { useEnvironment } from "@/contexts/environment-context"

interface ModelSelectorProps {
  selectedModel: string
  onModelChange: (modelId: string, modelName: string) => void
  disabled?: boolean
}

const getModelIcon = (modelName: string) => {
  if (modelName.includes("DeepSeek")) return <Zap className="h-4 w-4 text-purple-400" />
  if (modelName.includes("Llama")) return <Bot className="h-4 w-4 text-green-400" />
  return <Bot className="h-4 w-4 text-blue-400" />
}

const getStreamingSystemBadge = (streamingSystem: string) => {
  if (streamingSystem === 'deepseek-r1') {
    return <span className="text-xs px-1.5 py-0.5 bg-purple-900/30 text-purple-300 rounded border border-purple-700/50">R1</span>
  }
  if (streamingSystem === 'llama-stream') {
    return <span className="text-xs px-1.5 py-0.5 bg-green-900/30 text-green-300 rounded border border-green-700/50">3.1</span>
  }
  return <span className="text-xs px-1.5 py-0.5 bg-blue-900/30 text-blue-300 rounded border border-blue-700/50">1.5</span>
}

export function ModelSelector({ selectedModel, onModelChange, disabled = false }: ModelSelectorProps) {
  const { environment } = useEnvironment()
  const models = appConfig.chat.models.filter(m => m.active[environment])
  
  // Jika model yang dipilih tidak tersedia di environment ini, jangan ubah selectedModel
  // Hanya ambil model yang ada untuk ditampilkan
  let currentModel = models.find(m => m.id === selectedModel)
  
  // Jika model yang dipilih tidak tersedia, gunakan default HANYA untuk display
  // Tapi jangan trigger onModelChange
  if (!currentModel) {
    currentModel = models.find(m => m.isDefault) || models[0]
  }


  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          disabled={disabled}
          className={cn(
            "flex items-center gap-2 min-w-[140px] bg-background/60 backdrop-blur-sm border-border/50 hover:bg-background/80",
            disabled && "opacity-50 cursor-not-allowed"
          )}
        >
          {getModelIcon(currentModel.name)}
          <span className="truncate text-sm">{currentModel.name}</span>
          <ChevronDown className="h-3 w-3 ml-auto flex-shrink-0" />
        </Button>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent align="end" className="w-56 bg-background/95 backdrop-blur-md border-border/50">
        <DropdownMenuLabel className="text-xs font-medium text-muted-foreground">
          Select AI Model
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        
        {models.map((model: any) => (
          <DropdownMenuItem
            key={model.id}
            onClick={() => onModelChange(model.id, model.name)}
            className={cn(
              "flex items-start gap-2 p-2 cursor-pointer",
              currentModel.id === model.id && "bg-accent text-accent-foreground"
            )}
          >
            <div className="flex-shrink-0 mt-0.5">
              {getModelIcon(model.name)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm">{model.name}</div>
              <div className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                {model.description}
              </div>
              {model.streamingSystem && (
                <div className="mt-1">
                  {getStreamingSystemBadge(model.streamingSystem)}
                </div>
              )}
              {model.capabilities && (
                <div className="mt-2 space-y-1">
                  <div className="text-xs font-medium text-muted-foreground">Capabilities:</div>
                  {model.capabilities.slice(0, 2).map((capability: string, index: number) => (
                    <div key={index} className="text-xs text-muted-foreground">
                      • {capability}
                    </div>
                  ))}
                </div>
              )}
              {model.features && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {model.features.slice(0, 3).map((feature: string) => (
                    <span key={feature} className="text-xs px-1.5 py-0.5 bg-muted/50 text-muted-foreground rounded">
                      {feature.replace('-', ' ')}
                    </span>
                  ))}
                </div>
              )}
            </div>
            {currentModel.sessionId === model.sessionId && (
              <div className="w-2 h-2 rounded-full bg-primary flex-shrink-0 mt-2" />
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
