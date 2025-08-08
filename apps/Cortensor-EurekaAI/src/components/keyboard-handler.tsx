// src/components/keyboard-handler.tsx
"use client"

import { useEffect } from 'react'
import { useKeyboard } from '../hooks/use-keyboard'

export function KeyboardHandler({ children }: { children: React.ReactNode }) {
  const keyboard = useKeyboard()

  useEffect(() => {
    // Add professional body classes for keyboard state
    if (keyboard.isVisible) {
      document.body.classList.add('keyboard-visible')
      document.body.classList.add('keyboard-transition')
    } else {
      document.body.classList.remove('keyboard-visible')
    }

    // Professional viewport meta handling
    const viewport = document.querySelector('meta[name="viewport"]')
    if (viewport) {
      if (keyboard.isVisible) {
        viewport.setAttribute('content', 
          'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover, interactive-widget=resizes-content'
        )
      } else {
        viewport.setAttribute('content', 
          'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover'
        )
      }
    }

    return () => {
      document.body.classList.remove('keyboard-visible', 'keyboard-transition')
    }
  }, [keyboard.isVisible])

  // Professional body scroll lock during keyboard transition
  useEffect(() => {
    if (keyboard.isTransitioning) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }

    return () => {
      document.body.style.overflow = ''
    }
  }, [keyboard.isTransitioning])

  return <>{children}</>
}
