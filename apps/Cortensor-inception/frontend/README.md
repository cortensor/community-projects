# Inception — Frontend

Minimal Next.js frontend (TypeScript + Tailwind). This is a starter — replace mock auth with Firebase or Supabase integration.

Environment variables (optional):

- `NEXT_PUBLIC_BACKEND_URL` — base URL of the backend (default: `http://localhost:4000`).
- `NEXT_PUBLIC_SESSION_ID` — optional session id used by the Judge UI when submitting claims.


Quick start:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and click Login to call the backend demo `/infer-escrow` endpoint.
