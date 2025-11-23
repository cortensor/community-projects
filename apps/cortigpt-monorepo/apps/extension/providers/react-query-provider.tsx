'use client'

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import { useState } from "react"

export default function ReactQueryProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 10 * 60 * 1000, // 10 minute
        retry: 1,
        // refetchInterval: 10 * 1000, // 10 seconds
        // refetchIntervalInBackground: true,
      },
    },
  }))

  return (
    <QueryClientProvider client={queryClient}>
      {children}
        {/* <ReactQueryDevtools initialIsOpen={false} /> */}
    </QueryClientProvider>
  )
}