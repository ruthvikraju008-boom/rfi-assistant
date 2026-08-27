# Deploying "nexaminds" (RFI Knowledge Assistant) online — Streamlit Community Cloud

This gets you a real public URL (like `nexaminds.streamlit.app`), free, with
auto-redeploy every time you push to GitHub — the same workflow as Vercel,
just for Streamlit apps instead of Next.js ones.

## 1. Push this folder to GitHub

```bash
cd rfi-assistant
git init
git add .
git commit -m "Initial commit — RFI Knowledge Assistant"
```

Create a new **empty** repo on GitHub (no README/license, so there's no
merge conflict), e.g. `nexaminds-rfi-assistant`, then:

```bash
git branch -M main
git remote add origin https://github.com/<your-username>/nexaminds-rfi-assistant.git
git push -u origin main
```

## 2. Deploy on Streamlit Community Cloud

1. Go to **https://share.streamlit.io** and sign in with GitHub.
2. Click **"New app"**.
3. Pick:
   - Repository: `<your-username>/nexaminds-rfi-assistant`
   - Branch: `main`
   - Main file path: `app.py`
4. Click **"Advanced settings"** and set the **custom app URL / subdomain**
   to `nexaminds` (or whatever's available) — this becomes your live link:
   `https://nexaminds.streamlit.app`
5. Click **Deploy**. First build takes ~2-5 minutes.

## 3. (Optional) Add your API key for real AI drafts

Without this step the app still works fully — the Draft Assistant just uses
its built-in template fallback instead of a live LLM call.

1. On your deployed app, click the **"⋮"** menu (top right) → **Settings** → **Secrets**.
2. Paste:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-your-key-here"
   ANTHROPIC_MODEL = "claude-sonnet-5"
   ```
3. Save — the app restarts automatically with the key available.

## 4. Every future update

```bash
git add .
git commit -m "describe your change"
git push
```

Streamlit Cloud auto-redeploys on every push to `main` — no extra steps,
just like Vercel.

## Notes specific to this app

- **Database**: uses SQLite (`data/rfi_assistant.db`), auto-seeded on first
  run. On Streamlit Cloud the filesystem is not permanent — if the app
  goes to sleep and restarts, or you push a new commit, the DB resets back
  to the seeded demo data. That's fine for a hackathon/demo; if you need
  data to persist long-term, swap `DATABASE_URL` in `core/config.py` for a
  hosted Postgres URL (e.g. free tier on Supabase or Neon) — no other code
  changes needed since it's already SQLAlchemy-based.
- **Free tier resources**: 1 GB RAM. `requirements.txt` already excludes
  `sentence-transformers`/`torch` for this reason — the app automatically
  uses a lighter TF-IDF search backend instead, no functionality is lost.
- **Sleeping apps**: free Community Cloud apps sleep after inactivity and
  wake on the next visit (~10-30s cold start) — same idea as Vercel's
  serverless cold starts.
