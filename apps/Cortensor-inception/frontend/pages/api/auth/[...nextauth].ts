import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"

// Helpful runtime checks that surface missing env vars with clear errors
const clientId = process.env.GOOGLE_CLIENT_ID
const clientSecret = process.env.GOOGLE_CLIENT_SECRET
const nextAuthSecret = process.env.NEXTAUTH_SECRET
const nextAuthUrl = process.env.NEXTAUTH_URL

if (!clientId || !clientSecret) {
  // Throwing here gives a clear, early server-side error instead of the low-level openid-client error
  throw new Error(
    'Missing Google OAuth credentials: please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in frontend/.env.local (see .env.local.example)'
  )
}

if (!nextAuthUrl) {
  console.warn('[next-auth] NEXTAUTH_URL is not set. Set NEXTAUTH_URL in frontend/.env.local (e.g. http://localhost:3000)')
}

if (!nextAuthSecret) {
  console.warn('[next-auth] NEXTAUTH_SECRET is not set. Generate one with: openssl rand -base64 32')
}

export default NextAuth({
  providers: [
    GoogleProvider({
      clientId,
      clientSecret,
    }),
  ],
  session: { strategy: 'jwt' },
  secret: nextAuthSecret,
})
