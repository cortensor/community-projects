'use client'

import { AlertTriangle, Calendar, ExternalLink } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface DataFreshnessAlertProps {
  query: string
  answer: string
  currentDate: string
  className?: string
}

export function DataFreshnessAlert({ 
  query, 
  answer, 
  currentDate, 
  className 
}: DataFreshnessAlertProps) {
  
  // Check if the answer contains potentially outdated information
  const hasOldDates = /202[0-3]/.test(answer)
  const isCurrentQuery = /latest|recent|current|today|now|2024|2025|this year|this month/i.test(query)
  const shouldShowAlert = hasOldDates && isCurrentQuery

  if (!shouldShowAlert) return null

  const generateSearchLink = (query: string) => {
    // Use a static year to avoid hydration mismatch, update annually
    const currentYear = 2025
    const searchQuery = encodeURIComponent(`${query} ${currentYear}`)
    return `https://www.google.com/search?q=${searchQuery}`
  }

  return (
    <Card className={`border-orange-200 bg-orange-50 dark:bg-orange-900/20 ${className}`}>
      <CardContent className="p-4">
        <div className="flex items-start space-x-3">
          <AlertTriangle className="h-5 w-5 text-orange-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="text-sm font-medium text-orange-800 dark:text-orange-200">
              Information Currency Alert
            </div>
            <p className="text-sm text-orange-700 dark:text-orange-300">
              This response may contain outdated information. For the most current data about recent events, please verify independently.
            </p>
            <div className="flex items-center justify-between text-xs text-orange-600 dark:text-orange-400">
              <div className="flex items-center space-x-1">
                <Calendar className="h-3 w-3" />
                <span>Current date: {currentDate}</span>
              </div>
              <Button
                size="sm"
                variant="outline"
                className="h-6 px-2 text-xs border-orange-300 text-orange-700 hover:bg-orange-100"
                onClick={() => window.open(generateSearchLink(query), '_blank')}
              >
                <ExternalLink className="h-3 w-3 mr-1" />
                Verify Latest
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
