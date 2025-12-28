Phase 2 — Trust Gateway (Local)

Quick start (development):

1. Install deps

   cd backend && npm install

2. Prepare Prisma / SQLite DB

   npx prisma generate
   npx prisma db push

3. Run the backend

   npm run dev

Endpoint

POST http://localhost:3000/validate

Example body:

{
  "task": { "prompt": "Do not execute unsafe actions" },
  "policy": { "minValidators": 1, "minAgreement": 0.5 }
}

Expected behavior (Phase 2):
- Policy is validated deterministically
- Because there are no inference results yet, a valid policy yields ESCALATE
- Invalid policy yields BLOCK
- Every request creates a session and evidence bundle
