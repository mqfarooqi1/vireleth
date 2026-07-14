# Putting Vireleth online (real URL) + installing it as an app

You have two ways to get a public URL, plus an "Install" button that turns the
site into an app on your desktop or phone.

---

## Option A — Permanent URL (recommended): Render.com (free)

This gives you a stable HTTPS address like `https://vireleth.onrender.com` that
stays up 24/7, even when your PC is off.

1. Put this folder on **GitHub**:
   - Create a free account at <https://github.com> if you don't have one.
   - Make a new repository and upload everything in this folder (or use `git`).
2. Go to <https://render.com> and sign up (free, no card).
3. Click **New → Web Service** and connect your GitHub repo.
4. Render auto-detects the included `render.yaml`. Just confirm:
   - **Start command:** `python server.py`
   - **Plan:** Free
5. Click **Create Web Service**. In ~1–2 minutes you'll get your live URL.

To make it answer with full Claude conversations, add an environment variable in
the Render dashboard: **`ANTHROPIC_API_KEY` = your key**. (Without it, the live
site still works in demo mode.)

> Free Render services "sleep" after 15 minutes idle and wake on the next visit
> (first load takes a few extra seconds). Paid plans stay always-on.

**Other one-click hosts that work the same way:** Railway (<https://railway.app>),
Replit, or PythonAnywhere. All just run `python server.py`.

---

## Option B — Instant URL right now: a tunnel (no signup)

Great for showing someone immediately. The URL lasts only while your PC and the
tunnel are running, and it changes each time.

1. Start the app: `python server.py`
2. In a **second** terminal, run one of these (SSH is built into Windows):

   ```
   ssh -R 80:localhost:8000 nokey@localhost.run
   ```

   It prints a public `https://...` URL. Share that link. Press Ctrl+C to stop.

> ⚠️ While the tunnel is open, anyone with the link can use your chatbot. In
> demo mode that's harmless. **Once you add a Claude key, a shared link uses your
> API credits** — only share it when you mean to.

---

## Install it as an app 📱💻

Once you open the site (local or public URL) in Chrome or Edge:

- **Desktop:** click the **⬇ Install app** button in the top bar, or the install
  icon in the browser's address bar. It opens in its own window like a real app.
- **Phone (Android/Chrome):** menu → **Add to Home screen**.
- **iPhone (Safari):** Share → **Add to Home Screen**.

It gets its own icon and launches full-screen — no browser bars.

> Install requires **HTTPS**, so use the Render URL (Option A) or the tunnel URL
> (Option B) for the install button to appear. On plain `http://localhost` it
> also works because browsers treat localhost as secure.
