# Nexus AI 🤖

Your own **agentic, generative & predictive** AI chatbot — with a website to
navigate. One assistant, three switchable personalities:

| Mode | What it's for |
|------|----------------|
| ✨ **General** | An all-purpose assistant for anything |
| 🧬 **Domain Expert** | Genomics, bioinformatics & data analysis |
| 💼 **Business** | A client-facing helper that showcases your services |

Powered by Claude under the hood, with **agentic tool use** (calculator, clock,
trend forecaster) and a **predictive** linear-forecasting tool. It runs the
moment you start it — **no API key needed to try it** (demo mode), and no
packages to install.

---

## Quick start (Windows)

1. Open a terminal in this folder.
2. Run:

   ```
   python server.py
   ```

3. Open your browser at **http://127.0.0.1:8000**

That's it. With no API key you're in **demo mode**: the chat UI works and the
built-in tools (calculator, clock, forecaster) run for real — try
*"Forecast the trend of 12, 15, 14, 19, 23"* or *"What is (17.5/100)*2480?"*.

> There are **no dependencies to install** — it uses only the Python standard
> library. You just need Python 3 (you have 3.14).

---

## Go live with Claude (full conversations)

1. Get a Claude API key from <https://console.anthropic.com/> → **Settings → API keys**.
2. Copy `.env.example` to a new file named **`.env`** in this folder.
3. Paste your key into it:

   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

4. Restart: `python server.py`

You never paste secrets into the chat — the key lives only in your local `.env`
file, which is read by the server.

> Cost: you're billed per message by Anthropic (typically a fraction of a cent).
> Switch `ANTHROPIC_MODEL` in `.env` to `claude-haiku-4-5` for the cheapest option.

---

## Make it your own

Open `.env` (or `config.py`) and change:

- `BRAND` – the assistant's name (shown everywhere)
- `TAGLINE` – the subtitle under the name
- `OWNER` – the name used in Business mode ("… for **OWNER**'s services")

To change the personalities' behaviour, edit the `SYSTEM_PROMPTS` in
[`config.py`](config.py). To change the starter prompts and mode labels, edit
`MODES` in the same file.

---

## What's inside

```
python_code/
├── server.py        # the web server (stdlib only)
├── config.py        # branding, model, modes, system prompts  ← customise here
├── providers.py     # Claude API calls + agentic loop + demo fallback
├── tools.py         # the tools: calculator, clock, trend forecaster
├── static/          # the website (HTML / CSS / JS)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── .env.example     # copy to .env and add your key
└── README.md
```

## Feature map

- **Agentic** – the model decides when to call tools (calculator, clock,
  forecaster) and chains them together to answer.
- **Generative** – natural-language chat, writing, code, and explanations.
- **Predictive** – the `forecast_trend` tool fits a linear trend to your numbers
  and projects the next values. (Swap in a richer ML model later — it's one
  function in `tools.py`.)
- **Website** – a responsive, themable chat UI you fully own and can deploy.

---

## Next steps / ideas

- **Deploy online** so anyone can use it (a small cloud VM or a service like
  Render/Railway/Fly). Ask and I'll set that up.
- **Add tools** – give the bot new abilities (web search, database lookups,
  your own APIs) by adding to `tools.py`.
- **Add memory** – remember users across visits.
- **Streaming replies** – make answers appear word-by-word.
- **Image generation** – add a generative-images feature.
