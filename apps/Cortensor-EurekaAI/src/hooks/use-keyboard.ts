// src/hooks/use-keyboard.ts
"use client"

import { useState, useEffect } from 'react'

interface KeyboardState {
  isVisible: boolean
  height: number
  isTransitioning: boolean
}

export function useKeyboard() {
  const [keyboardState, setKeyboardState] = useState<KeyboardState>({
    isVisible: false,
    height: 0,
    isTransitioning: false
  })

  useEffect(() => {
    // Only run on client side and mobile devices
    if (typeof window === 'undefined') return
    
    const isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      navigator.userAgent
    )
    
    if (!isMobile) return

    let timeoutId: NodeJS.Timeout
    const initialViewportHeight = window.innerHeight
    
    // Simplified and more stable keyboard detection
    const updateKeyboardState = () => {
      const currentHeight = window.visualViewport?.height || window.innerHeight
      const heightDifference = initialViewportHeight - currentHeight
      const isKeyboardVisible = heightDifference > 150 // Stable threshold
      
      setKeyboardState({
        isVisible: isKeyboardVisible,
        height: isKeyboardVisible ? heightDifference : 0,
        isTransitioning: false
      })
    }

    const handleViewportChange = () => {
      // Clear any existing timeout to prevent multiple rapid updates
      clearTimeout(timeoutId)
      
      setKeyboardState(prev => ({ ...prev, isTransitioning: true }))
      
      // Debounce with longer delay for stability
      timeoutId = setTimeout(updateKeyboardState, 200)
    }
    // Use Visual Viewport API for better keyboard detection
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', handleViewportChange)
    } else {
      // Fallback to window resize for older browsers
      window.addEventListener('resize', handleViewportChange)
    }

    return () => {
      clearTimeout(timeoutId)
      if (window.visualViewport) {
        window.visualViewport.removeEventListener('resize', handleViewportChange)
      } else {
        window.removeEventListener('resize', handleViewportChange)
      }
    }
  }, [])

  return keyboardState
}
