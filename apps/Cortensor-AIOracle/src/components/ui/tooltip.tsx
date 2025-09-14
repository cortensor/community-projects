import React, { useState } from 'react'

function cn(...inputs: (string | undefined)[]): string {
  return inputs.filter(Boolean).join(' ')
}

interface TooltipProps {
  children: React.ReactNode
  content: React.ReactNode
  className?: string
}

export function Tooltip({ children, content, className }: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false)

  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onClick={() => setIsVisible(!isVisible)}
        className="cursor-pointer"
      >
        {children}
      </div>
      {isVisible && (
        <div className={cn(
          "absolute z-50 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg min-w-[300px] max-w-[400px]",
          "bottom-full left-1/2 transform -translate-x-1/2 mb-2",
          "animate-in fade-in-0 zoom-in-95 duration-200",
          className
        )}>
          <div className="text-sm text-gray-900 dark:text-gray-100">
            {content}
          </div>
          {/* Arrow */}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2">
            <div className="border-8 border-transparent border-t-white dark:border-t-gray-800"></div>
            <div className="absolute top-[-9px] left-[-8px] border-8 border-transparent border-t-gray-200 dark:border-t-gray-700"></div>
          </div>
        </div>
      )}
    </div>
  )
}
