"""
Central configuration for the AI chatbot.

Everything you'd want to rebrand or tune lives here. You can also override any
of these with environment variables or a .env file (see .env.example).

Zero third-party dependencies — pure Python standard library.
"""

import os

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(PROJECT_DIR, "static")
ENV_FILE = os.path.join(PROJECT_DIR, ".env")


# ---------------------------------------------------------------------------
# Tiny .env loader (no external library needed)
# ---------------------------------------------------------------------------
def _load_env_file(path):
    """Read KEY=VALUE lines from a .env file. Real env vars win over the file."""
    values = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                values[key] = val
    return values


_ENV = _load_env_file(ENV_FILE)


def get(name, default=None):
    """Look up a setting: real environment variable first, then .env, then default."""
    if name in os.environ and os.environ[name] != "":
        return os.environ[name]
    if name in _ENV and _ENV[name] != "":
        return _ENV[name]
    return default


# ---------------------------------------------------------------------------
# Branding — change these to make the assistant your own
# ---------------------------------------------------------------------------
BRAND = get("BRAND", "Vireleth")
TAGLINE = get("TAGLINE", "Living intelligence · agentic, generative & predictive.")
OWNER = get("OWNER", "our team")  # used in the Business / client-facing mode


# ---------------------------------------------------------------------------
# Model / API settings
# ---------------------------------------------------------------------------
API_URL = "https://api.anthropic.com/v1/messages"
API_KEY = get("ANTHROPIC_API_KEY", "")
# Default to Claude's most capable model. Swap for cost/speed if you like:
#   claude-haiku-4-5   -> cheapest & fastest
#   claude-sonnet-5    -> balanced
#   claude-opus-4-8    -> most capable (default)
MODEL = get("ANTHROPIC_MODEL", "claude-opus-4-8")
MAX_TOKENS = int(get("MAX_TOKENS", "4096"))
MAX_TOOL_ITERS = 6  # safety cap on the agentic tool-use loop

# --- Google Gemini (FREE tier: get a key at https://aistudio.google.com/apikey) ---
GEMINI_API_KEY = get("GEMINI_API_KEY", "")
GEMINI_MODEL = get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Pick the engine automatically from whichever key is present.
if API_KEY:
    PROVIDER = "anthropic"   # paid, most capable
elif GEMINI_API_KEY:
    PROVIDER = "gemini"      # FREE
else:
    PROVIDER = "demo"        # no key -> local tools only

# True when no AI key is configured -> the app runs in a clickable DEMO mode.
DEMO_MODE = PROVIDER == "demo"

# Name of the active engine (shown in the UI status pill).
ENGINE_NAME = {"anthropic": MODEL, "gemini": GEMINI_MODEL, "demo": "demo"}[PROVIDER]


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
HOST = get("HOST", "127.0.0.1")
PORT = int(get("PORT", "8000"))


# ---------------------------------------------------------------------------
# The three personalities. Each has its own system prompt + starter prompts.
# ---------------------------------------------------------------------------
def _system_prompts():
    return {
        "general": (
            f"You are {BRAND}, a helpful, knowledgeable general-purpose AI assistant. "
            "You can use tools to run calculations, get the current date and time, and "
            "forecast simple numeric trends. Be friendly, clear, and concise. "
            "Format answers with short paragraphs, bullet points, or code blocks where "
            "helpful. Respond directly, without unnecessary preamble."
        ),
        "domain": (
            f"You are {BRAND} in Domain Expert mode, specialised in genomics, "
            "bioinformatics, statistics, and data analysis (R and Python). "
            "Give precise, technically accurate answers for scientific and data work, "
            "with correct terminology and code examples where relevant. Use tools for "
            "calculations and trend forecasts when they help. If something is uncertain "
            "or outside your knowledge, say so plainly rather than guessing."
        ),
        "business": (
            f"You are {BRAND}, the assistant for {OWNER}'s freelance data & analytics "
            "services (data analysis, dashboards, R packages, workflow automation, and "
            "bioinformatics). Be warm, professional, and genuinely helpful to prospective "
            "clients. Explain what the services can do, answer questions clearly, and "
            "gently encourage interested visitors to get in touch. Do NOT invent specific "
            "prices, timelines, or availability — instead offer to connect them directly. "
            "Keep replies concise and approachable."
        ),
    }


SYSTEM_PROMPTS = _system_prompts()

# Metadata sent to the browser to build the UI.
MODES = [
    {
        "id": "general",
        "name": "General",
        "icon": "✨",  # sparkles
        "desc": "An all-purpose assistant for anything.",
        "placeholder": "Ask me anything…",
        "suggestions": [
            "Explain quantum computing simply",
            "What is 17.5% of 2,480?",
            "Give me a 3-day plan to learn Python",
        ],
    },
    {
        "id": "domain",
        "name": "Domain Expert",
        "icon": "\U0001f9ec",  # DNA
        "desc": "Genomics, bioinformatics & data analysis.",
        "placeholder": "Ask about genomics, stats or data…",
        "suggestions": [
            "Difference between RNA-seq and scRNA-seq?",
            "Forecast the trend of 12, 15, 14, 19, 23",
            "Write an R function to normalise a vector",
        ],
    },
    {
        "id": "business",
        "name": "Business",
        "icon": "\U0001f4bc",  # briefcase
        "desc": "Client-facing helper for your services.",
        "placeholder": "How can we help your project?",
        "suggestions": [
            "What services do you offer?",
            "Can you build me a data dashboard?",
            "How do I get started with a project?",
        ],
    },
]


def client_config():
    """The subset of config that is safe to send to the browser."""
    return {
        "brand": BRAND,
        "tagline": TAGLINE,
        "owner": OWNER,
        "model": ENGINE_NAME,
        "demo": DEMO_MODE,
        "modes": MODES,
    }
