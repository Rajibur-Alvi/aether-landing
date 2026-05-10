# Aether Backend — Deploy Checklist

## BEFORE YOU PUSH: Collect these backend values first

| # | Key | Where to get it |
|---|-----|-----------------|
| 1 | `GROQ_API_KEY` | console.groq.com → API Keys |
| 2 | `PINECONE_API_KEY` | app.pinecone.io → API Keys |
| 3 | `SUPABASE_URL` | Supabase Dashboard → Settings → API → Project URL |
| 4 | `SUPABASE_SERVICE_KEY` | Supabase Dashboard → Settings → API → service_role key |
| 5 | `SUPABASE_JWT_SECRET` | Supabase Dashboard → Settings → API → JWT Secret |
| 6 | Lemon Squeezy values | API key, store ID, and Signal/Signal Pro variant IDs |
| 7 | Your Render URL | Set after Step 4 (e.g. https://aether-landing.onrender.com) |

---

## Step 1 — Pinecone Index (2 min)

1. Go to app.pinecone.io → Create Index
2. Name: `entropy-vectors`
3. Dimension: **768**
4. Metric: **cosine**
5. Cloud: aws / us-east-1
6. Click Create

---

## Step 2 — Supabase Schema (2 min)

1. Go to your Supabase project → SQL Editor
2. Copy the entire contents of `supabase/migrations/001_initial_schema.sql`
3. Paste and click Run
4. While here, collect keys 3, 4, 5 from Settings → API

---

## Step 3 — Push to GitHub (1 min)

Copy the `backend/`, `supabase/`, and `frontend-lib/` folders into your existing repo.
Then:

```bash
git add .
git commit -m "feat: add entropy backend"
git push
```

---

## Step 4 — Deploy to Render (5 min)

1. Go to dashboard.render.com → New → Web Service
2. Connect your GitHub repo
3. Settings:
   - Root Directory: `backend`
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`
   - Plan: Free
4. Add these Environment Variables:

```
GROQ_API_KEY=           ← your value
PINECONE_API_KEY=       ← your value
PINECONE_INDEX_NAME=entropy-vectors
SUPABASE_URL=           ← your value
SUPABASE_SERVICE_KEY=   ← your value
SUPABASE_JWT_SECRET=    ← your value
LEMONSQUEEZY_API_KEY=   ← your value
LEMONSQUEEZY_STORE_ID=  ← your value
LEMONSQUEEZY_SIGNAL_VARIANT_ID=      ← your value
LEMONSQUEEZY_SIGNAL_PRO_VARIANT_ID=  ← your value
APP_URL=https://your-frontend-url
CORS_ORIGINS_RAW=https://your-frontend-url
ENVIRONMENT=production
```

5. Click Create Web Service
6. Wait for build to finish — note your Render URL

---

## Step 5 — Add Frontend Env Vars to Vercel (2 min)

In Vercel → your project → Settings → Environment Variables:

```
VITE_BACKEND_URL=https://your-render-url.onrender.com
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-public-key
```

Redeploy on Vercel after adding these.

---

## Step 6 — Copy frontend-lib into your project (1 min)

```bash
cp frontend-lib/api.ts          your-frontend/src/lib/api.ts
cp frontend-lib/useEntropyChat.ts  your-frontend/src/hooks/useEntropyChat.ts
```

> The repo also includes `index.html`, a static landing page demo that uses `/api/public/*` for two free trials and then shows a subscription prompt instead of a Google Form.

---

## Step 7 — Verify (2 min)

1. Health check: `https://your-backend.onrender.com/api/health`
   - Should return `{"status":"operational",...}`
2. API docs: `https://your-backend.onrender.com/docs`
3. Sign up a user on your frontend
4. Ingest a text document via `/api/ingest/text`
5. Ask a question via `/api/chat/ask`

---

## Step 8 — Prevent Cold Starts (2 min)

Go to uptimerobot.com (free account):
- New Monitor → HTTP(s)
- URL: `https://your-backend.onrender.com/api/health`
- Interval: 5 minutes

This keeps Render's free tier awake.

---

## ⚠️ Security Rules

- NEVER put `SUPABASE_SERVICE_KEY` in Vercel — server only
- NEVER put `SUPABASE_JWT_SECRET` in Vercel — server only
- `VITE_SUPABASE_ANON_KEY` is safe for frontend (respects RLS)

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| 30s cold start | Set up UptimeRobot (Step 8) |
| "Vector search failed" | Check Pinecone index exists, dim=768, key is correct |
| "Groq inference failed" | Check GROQ_API_KEY in Render |
| 401 Invalid token | Check SUPABASE_JWT_SECRET matches your Supabase project |
| "Metadata storage failed" | Re-run the SQL migration |
| CORS error | Add your frontend URL to `CORS_ORIGINS_RAW` on Render |
