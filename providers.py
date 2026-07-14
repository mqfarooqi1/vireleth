"""
The "brain" behind the chatbot.

Two paths:
  * chat_with_claude()  -> real, agentic Claude API calls (used when a key is set)
  * chat_demo()         -> a smart local fallback so the site works with no key

Both return: {"reply": str, "tools_used": [str], "demo": bool}

Uses only the Python standard library (urllib) to call the Anthropic API, so
there are no packages to install.
"""

import json
import re
import urllib.error
import urllib.request

import config
import tools


# ---------------------------------------------------------------------------
# Real Claude path — with an agentic tool-use loop
# ---------------------------------------------------------------------------
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

    # Client history arrives as [{role, content(str)}]; we extend it in-loop.
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
            # Record the assistant turn (including the tool_use blocks) …
            convo.append({"role": "assistant", "content": content})
            # … run each requested tool and send the results back.
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
            continue  # loop again so the model can use the results

        if stop_reason == "refusal":
            return {
                "reply": "I'm not able to help with that particular request, but I'm "
                "happy to help with something else.",
                "tools_used": tools_used,
                "demo": False,
            }

        # Normal completion — collect the text blocks.
        text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
        return {
            "reply": text.strip() or "(no response)",
            "tools_used": tools_used,
            "demo": False,
        }

    return {
        "reply": "I did a lot of tool work but couldn't quite wrap up — try rephrasing?",
        "tools_used": tools_used,
        "demo": False,
    }


# ---------------------------------------------------------------------------
# Demo path — no API key required, still shows off the real tools
# ---------------------------------------------------------------------------
_MATH_RE = re.compile(r"[-+]?\d[\d\s.,]*\s*[-+*/^%()][\d\s.,+\-*/^%()]*\d")


def _demo_intro(mode):
    brand = config.BRAND
    if mode == "domain":
        return (
            f"**{brand} — Domain Expert (demo)**. I specialise in genomics, "
            "bioinformatics and data analysis. Add a Claude API key to unlock full "
            "answers. Meanwhile, try a **calculation** or a **forecast** — those run "
            "locally right now."
        )
    if mode == "business":
        return (
            f"**{brand} — Business (demo)**. I help visitors learn about "
            f"{config.OWNER}'s data & analytics services. Add a Claude API key for "
            "full conversations. You can still try the built-in **calculator** and "
            "**trend forecaster**."
        )
    return (
        f"**{brand} (demo mode)**. I'm running without a Claude API key, so full "
        "conversational answers are switched off — but my **agentic tools** are live. "
        "Try:\n\n"
        "- `What is (17.5/100) * 2480?`\n"
        "- `Forecast the trend of 12, 15, 14, 19, 23`\n"
        "- `What time is it?`"
    )


def chat_demo(messages, mode):
    """A lightweight local responder that runs the real tools where it can."""
    last = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last = m.get("content", "")
            break
    text = last.strip()
    lower = text.lower()
    tools_used = []

    # 1) Date / time
    if any(w in lower for w in ("what time", "what's the time", "what day", "today", "date", "time now")):
        tools_used.append("current_datetime")
        result = tools.run_tool("current_datetime", {})
        return {"reply": result, "tools_used": tools_used, "demo": True}

    # 2) Forecast (needs 3+ numbers and forecast intent)
    if any(w in lower for w in ("forecast", "predict", "trend", "project", "projection")):
        nums = tools.extract_numbers(text)
        if len(nums) >= 3:
            tools_used.append("forecast_trend")
            result = tools.run_tool("forecast_trend", {"values": nums, "periods": 3})
            return {
                "reply": f"Using your series {nums}:\n\n{result}",
                "tools_used": tools_used,
                "demo": True,
            }

    # 3a) "X% of Y" phrasing (common natural-language calculation)
    pct = re.search(r"(-?\d[\d.]*)\s*%\s*of\s*([\d.,]+)", lower)
    if pct:
        try:
            p = float(pct.group(1))
            base = float(pct.group(2).replace(",", ""))
            value = tools.calculate(f"({p}/100)*{base}")
            tools_used.append("calculator")
            return {
                "reply": f"{pct.group(1)}% of {pct.group(2)} = **{value}**",
                "tools_used": tools_used,
                "demo": True,
            }
        except Exception:
            pass

    # 3b) Arithmetic
    match = _MATH_RE.search(text)
    if match:
        expr = match.group(0).replace(",", "")
        try:
            value = tools.calculate(expr)
            tools_used.append("calculator")
            return {
                "reply": f"`{expr.strip()}` = **{value}**",
                "tools_used": tools_used,
                "demo": True,
            }
        except Exception:
            pass  # fall through to the intro message

    # 4) Anything else -> a friendly, mode-aware demo message
    return {"reply": _demo_intro(mode), "tools_used": tools_used, "demo": True}


# ---------------------------------------------------------------------------
# Public entry point used by the server
# ---------------------------------------------------------------------------
def chat(messages, mode):
    if config.DEMO_MODE:
        return chat_demo(messages, mode)
    try:
        return chat_with_claude(messages, mode)
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            pass
        # Common case: bad / missing key -> guide the user, fall back to demo.
        friendly = {
            401: "The Claude API key looks invalid. Check ANTHROPIC_API_KEY in your .env.",
            403: "The Claude API key doesn't have access to this model.",
            429: "Rate limit reached — please wait a moment and try again.",
        }.get(exc.code, f"Claude API error {exc.code}.")
        return {
            "reply": f"⚠️ {friendly}",
            "tools_used": [],
            "demo": False,
            "error": detail[:400],
        }
    except Exception as exc:  # network etc.
        return {
            "reply": f"⚠️ Could not reach the Claude API: {exc}",
            "tools_used": [],
            "demo": False,
        }
