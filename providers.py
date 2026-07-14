"""
The "brain" behind the chatbot.

Supports three engines, chosen automatically by which key is present:
  * Claude   (ANTHROPIC_API_KEY)  -> real agentic tool-use loop (paid)
  * Gemini   (GEMINI_API_KEY)     -> real conversations, FREE (Google AI Studio)
  * Demo     (no key)             -> local tools only, still clickable

All paths return: {"reply": str, "tools_used": [str], "demo": bool}

Uses only the Python standard library (urllib), so there is nothing to install.
"""

import json
import re
import urllib.error
import urllib.request

import config
import tools


# ===========================================================================
# Claude (paid) — agentic tool-use loop
# ===========================================================================
def _post_anthropic(payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(config.API_URL, data=data, method="POST")
    req.add_header("content-type", "application/json")
    req.add_header("x-api-key", config.API_KEY)
    req.add_header("anthropic-version", "2023-06-01")
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat_with_claude(messages, mode):
    """Send the conversation to Claude, running any tools it asks for."""
    system_prompt = config.SYSTEM_PROMPTS.get(mode, config.SYSTEM_PROMPTS["general"])
    convo = [{"role": m["role"], "content": m["content"]} for m in messages]
    tools_used = []

    for _ in range(config.MAX_TOOL_ITERS):
        payload = {
            "model": config.MODEL,
            "max_tokens": config.MAX_TOKENS,
            "system": system_prompt,
            "messages": convo,
            "tools": tools.TOOL_DEFS,
        }
        resp = _post_anthropic(payload)
        content = resp.get("content", [])
        stop_reason = resp.get("stop_reason")

        if stop_reason == "tool_use":
            convo.append({"role": "assistant", "content": content})
            tool_results = []
            for block in content:
                if block.get("type") == "tool_use":
                    name = block.get("name", "")
                    tools_used.append(name)
                    result = tools.run_tool(name, block.get("input", {}))
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.get("id"),
                            "content": result,
                        }
                    )
            convo.append({"role": "user", "content": tool_results})
            continue

        if stop_reason == "refusal":
            return {
                "reply": "I'm not able to help with that particular request, but I'm "
                "happy to help with something else.",
                "tools_used": tools_used,
                "demo": False,
            }

        text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
        return {"reply": text.strip() or "(no response)", "tools_used": tools_used, "demo": False}

    return {
        "reply": "I did a lot of tool work but couldn't quite wrap up — try rephrasing?",
        "tools_used": tools_used,
        "demo": False,
    }


# ===========================================================================
# Built-in tools shared by the free & demo paths (exact, deterministic)
# ===========================================================================
_MATH_RE = re.compile(r"[-+]?\d[\d\s.,]*\s*[-+*/^%()][\d\s.,+\-*/^%()]*\d")


def _last_user(messages):
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def local_tools(messages):
    """If the latest message maps to a built-in tool, run it. Else return None."""
    text = _last_user(messages).strip()
    lower = text.lower()

    # Date / time
    if any(w in lower for w in ("what time", "what's the time", "what day", "today", "date", "time now")):
        return {"reply": tools.run_tool("current_datetime", {}), "tools_used": ["current_datetime"]}

    # Forecast (needs 3+ numbers and forecast intent)
    if any(w in lower for w in ("forecast", "predict", "trend", "project", "projection")):
        nums = tools.extract_numbers(text)
        if len(nums) >= 3:
            result = tools.run_tool("forecast_trend", {"values": nums, "periods": 3})
            return {"reply": f"Using your series {nums}:\n\n{result}", "tools_used": ["forecast_trend"]}

    # "X% of Y" phrasing
    pct = re.search(r"(-?\d[\d.]*)\s*%\s*of\s*([\d.,]+)", lower)
    if pct:
        try:
            p = float(pct.group(1))
            base = float(pct.group(2).replace(",", ""))
            value = tools.calculate(f"({p}/100)*{base}")
            return {"reply": f"{pct.group(1)}% of {pct.group(2)} = **{value}**", "tools_used": ["calculator"]}
        except Exception:
            pass

    # Plain arithmetic
    match = _MATH_RE.search(text)
    if match:
        expr = match.group(0).replace(",", "")
        try:
            value = tools.calculate(expr)
            return {"reply": f"`{expr.strip()}` = **{value}**", "tools_used": ["calculator"]}
        except Exception:
            pass

    return None


# ===========================================================================
# Gemini (FREE) — real conversations via Google AI Studio
# ===========================================================================
def _post_gemini(system_prompt, messages):
    contents = []
    for m in messages:
        role = "model" if m.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": str(m.get("content", ""))}]})
    body = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": config.MAX_TOKENS, "temperature": 0.7},
    }
    url = f"{config.GEMINI_URL}/{config.GEMINI_MODEL}:generateContent"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("content-type", "application/json")
    req.add_header("x-goog-api-key", config.GEMINI_API_KEY)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat_with_gemini(messages, mode):
    """Free conversations. Built-in tools answer exactly; everything else -> Gemini."""
    hit = local_tools(messages)
    if hit:
        hit["demo"] = False
        return hit

    system_prompt = config.SYSTEM_PROMPTS.get(mode, config.SYSTEM_PROMPTS["general"])
    data = _post_gemini(system_prompt, messages)

    text = ""
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
    except Exception:
        reason = ""
        try:
            reason = data["candidates"][0].get("finishReason", "")
        except Exception:
            reason = (data.get("promptFeedback", {}) or {}).get("blockReason", "")
        if reason in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST"):
            text = "I can't help with that one, but I'm happy to help with something else."
        else:
            text = "I couldn't generate a response to that — try rephrasing?"

    return {"reply": text.strip() or "(no response)", "tools_used": [], "demo": False}


# ===========================================================================
# Demo (no key) — local tools only
# ===========================================================================
def _demo_intro(mode):
    brand = config.BRAND
    if mode == "domain":
        return (
            f"**{brand} — Domain Expert (demo)**. I specialise in genomics, "
            "bioinformatics and data analysis. Add a free Gemini key to unlock full "
            "answers. Meanwhile, try a **calculation** or a **forecast** — those run now."
        )
    if mode == "business":
        return (
            f"**{brand} — Business (demo)**. I help visitors learn about "
            f"{config.OWNER}'s data & analytics services. Add a free Gemini key for "
            "full conversations. You can still try the built-in **calculator** and "
            "**trend forecaster**."
        )
    return (
        f"**{brand} (demo mode)**. I'm running without an AI key, so full "
        "conversational answers are switched off — but my **agentic tools** are live. "
        "Try:\n\n"
        "- `What is (17.5/100) * 2480?`\n"
        "- `Forecast the trend of 12, 15, 14, 19, 23`\n"
        "- `What time is it?`"
    )


def chat_demo(messages, mode):
    hit = local_tools(messages)
    if hit:
        hit["demo"] = True
        return hit
    return {"reply": _demo_intro(mode), "tools_used": [], "demo": True}


# ===========================================================================
# Public entry point used by the server
# ===========================================================================
def chat(messages, mode):
    provider = config.PROVIDER
    try:
        if provider == "anthropic":
            return chat_with_claude(messages, mode)
        if provider == "gemini":
            return chat_with_gemini(messages, mode)
        return chat_demo(messages, mode)
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            pass
        if provider == "gemini":
            friendly = {
                400: "The Gemini API key looks invalid. Check GEMINI_API_KEY.",
                403: "The Gemini API key was rejected. Check GEMINI_API_KEY.",
                404: "That Gemini model wasn't found — try setting GEMINI_MODEL to gemini-2.0-flash.",
                429: "Free Gemini limit reached for now — wait a minute and try again.",
            }.get(exc.code, f"Gemini API error {exc.code}.")
        else:
            friendly = {
                401: "The Claude API key looks invalid. Check ANTHROPIC_API_KEY.",
                403: "The Claude API key doesn't have access to this model.",
                429: "Rate limit reached — please wait a moment and try again.",
            }.get(exc.code, f"Claude API error {exc.code}.")
        return {"reply": f"⚠️ {friendly}", "tools_used": [], "demo": False, "error": detail[:400]}
    except Exception as exc:
        return {"reply": f"⚠️ Could not reach the AI service: {exc}", "tools_used": [], "demo": False}
