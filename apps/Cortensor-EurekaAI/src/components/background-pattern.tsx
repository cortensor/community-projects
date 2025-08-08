"use client"

import { useEffect, useState } from "react"

export function BackgroundPattern() {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) return null

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden">
      {/* Main Gradient Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-rose-100 via-purple-50 to-blue-100 dark:from-rose-950/20 dark:via-purple-950/20 dark:to-blue-950/20" />

      {/* Secondary Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/10 to-purple-200/30 dark:from-transparent dark:via-white/5 dark:to-purple-900/20" />

      {/* Geometric Pattern Overlay */}
      <div className="absolute inset-0 opacity-[0.03] dark:opacity-[0.08]">
        <svg
          className="absolute inset-0 h-full w-full"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 1000 1000"
          preserveAspectRatio="xMidYMid slice"
        >
          <defs>
            <pattern id="geometric-pattern" x="0" y="0" width="100" height="100" patternUnits="userSpaceOnUse">
              <path
                d="M20 20L40 40M60 20L80 40M20 60L40 80M60 60L80 80"
                stroke="currentColor"
                strokeWidth="1"
                fill="none"
              />
              <circle cx="50" cy="50" r="2" fill="currentColor" opacity="0.3" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#geometric-pattern)" />
        </svg>
      </div>

      {/* Floating Geometric Elements */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Large Chevron - Top Right */}
        <div className="absolute -top-20 -right-20 w-96 h-96 opacity-[0.02] dark:opacity-[0.05] rotate-12">
          <svg viewBox="0 0 100 100" className="w-full h-full">
            <path
              d="M20 30 L50 10 L80 30 L80 35 L50 15 L20 35 Z M20 45 L50 25 L80 45 L80 50 L50 30 L20 50 Z"
              fill="currentColor"
            />
          </svg>
        </div>

        {/* Medium Chevron - Bottom Left */}
        <div className="absolute -bottom-16 -left-16 w-64 h-64 opacity-[0.02] dark:opacity-[0.05] -rotate-12">
          <svg viewBox="0 0 100 100" className="w-full h-full">
            <path
              d="M30 20 L50 40 L70 20 L75 20 L50 45 L25 20 Z M30 35 L50 55 L70 35 L75 35 L50 60 L25 35 Z"
              fill="currentColor"
            />
          </svg>
        </div>

        {/* Small Accent Elements */}
        <div className="absolute top-1/4 right-1/4 w-8 h-8 opacity-[0.03] dark:opacity-[0.06] rotate-45">
          <div className="w-full h-full border border-current rounded-sm" />
        </div>

        <div className="absolute bottom-1/3 left-1/3 w-6 h-6 opacity-[0.03] dark:opacity-[0.06] rotate-12">
          <div className="w-full h-full bg-current rounded-full" />
        </div>

        <div className="absolute top-1/2 left-1/4 w-4 h-4 opacity-[0.03] dark:opacity-[0.06] -rotate-12">
          <div className="w-full h-full border border-current transform rotate-45" />
        </div>
      </div>

      {/* Subtle Noise Texture */}
      <div
        className="absolute inset-0 opacity-[0.015] dark:opacity-[0.03] mix-blend-overlay"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />
    </div>
  )
}
