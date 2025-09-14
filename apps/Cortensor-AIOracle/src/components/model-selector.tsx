import React from 'react'
import { Check, ChevronDown, Bot, Zap, Brain } from 'lucide-react'
import { ModelConfig } from '../lib/models'

interface ModelSelectorProps {
  models: ModelConfig[]
  selectedModel: ModelConfig
  onModelChange: (model: ModelConfig) => void
  disabled?: boolean
}

const getModelIcon = (modelId: string) => {
  switch (modelId) {
    case 'llava-1.5':
      return <Bot className="w-4 h-4 text-blue-500" />
    case 'deepseek-r1':
      return <Brain className="w-4 h-4 text-purple-500" />
    default:
      return <Bot className="w-4 h-4 text-gray-500" />
  }
}

const getModelBadgeColor = (modelId: string) => {
  switch (modelId) {
    case 'llava-1.5':
      return 'bg-blue-50 border-blue-200 text-blue-700'
    case 'deepseek-r1':
      return 'bg-purple-50 border-purple-200 text-purple-700'
    default:
      return 'bg-gray-50 border-gray-200 text-gray-700'
  }
}

export function ModelSelector({ models, selectedModel, onModelChange, disabled }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = React.useState(false)

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          w-full min-w-[200px] px-3 py-2 border rounded-lg bg-white text-left
          flex items-center justify-between gap-2 transition-colors
          ${disabled 
            ? 'border-gray-200 text-gray-400 cursor-not-allowed' 
            : 'border-gray-300 hover:border-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20'
          }
        `}
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {getModelIcon(selectedModel.id)}
          <div className="flex flex-col min-w-0">
            <span className="font-medium text-sm truncate">
              {selectedModel.displayName}
            </span>
            {/* Session hidden on UI as requested */}
          </div>
        </div>
        <ChevronDown 
          className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} 
        />
      </button>

      {isOpen && !disabled && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg z-20 max-h-64 overflow-y-auto">
            {models.map((model) => (
              <button
                key={model.id}
                type="button"
                onClick={() => {
                  onModelChange(model)
                  setIsOpen(false)
                }}
                className={`
                  w-full px-3 py-3 text-left hover:bg-gray-50 border-b border-gray-100 last:border-b-0
                  flex items-start gap-3 transition-colors
                `}
              >
                <div className="flex-shrink-0 mt-0.5">
                  {getModelIcon(model.id)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-sm text-gray-900">
                      {model.displayName}
                    </span>
                    {selectedModel.id === model.id && (
                      <Check className="w-4 h-4 text-blue-500" />
                    )}
                  </div>
                  <p className="text-xs text-gray-600 mb-2 line-clamp-2">
                    {model.description}
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {model.capabilities.slice(0, 2).map((capability) => (
                      <span
                        key={capability}
                        className={`
                          inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium border
                          ${getModelBadgeColor(model.id)}
                        `}
                      >
                        {capability}
                      </span>
                    ))}
                    {model.capabilities.length > 2 && (
                      <span className="text-xs text-gray-400">
                        +{model.capabilities.length - 2} more
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                    {/* Session hidden on UI; keep other meta */}
                    <span>{model.timeout}s timeout</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
