import '../styles/globals.css'
import { SessionProvider } from 'next-auth/react'

type AppProps = { Component: any; pageProps: any; session?: any }

export default function App({ Component, pageProps, session }: AppProps) {
  return (
    <SessionProvider session={session}>
      <Component {...pageProps} />
    </SessionProvider>
  )
}
