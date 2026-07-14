"""
Agentic tools the assistant can call, plus a predictive forecasting tool.

These give the bot real "agentic" abilities (it decides when to call them) and a
genuine "predictive" capability (linear trend forecasting). Everything here is
pure standard-library Python and completely safe — no shell, no file access, no
network. The calculator uses a restricted AST evaluator, never `eval()`.
"""

import ast
import json
import operator
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Tool schemas advertised to the model (Anthropic tool-use format)
# ---------------------------------------------------------------------------
TOOL_DEFS = [
    {
        "name": "calculator",
        "description": (
            "Evaluate a mathematical expression and return the numeric result. "
            "Use this whenever the user asks for arithmetic, percentages, or any "
            "calculation. Supports + - * / // % ** and parentheses."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The math expression, e.g. '(17.5/100)*2480'",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "name": "current_datetime",
        "description": (
            "Get the current local and UTC date and time. Use this when the user "
            "asks what day or time it is, or needs today's date."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "forecast_trend",
        "description": (
            "Predict future values from a series of numbers using a linear trend "
            "(least-squares regression). Use this when the user asks to forecast, "
            "project, or predict where a sequence of numbers is heading."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "The historical numbers in order, oldest first.",
                },
                "periods": {
                    "type": "integer",
                    "description": "How many future periods to predict (default 3).",
                },
            },
            "required": ["values"],
        },
    },
]


# ---------------------------------------------------------------------------
# Safe arithmetic evaluator (no eval)
# ---------------------------------------------------------------------------
_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Unsupported or unsafe expression")


def calculate(expression):
    """Evaluate a math expression safely. Accepts '^' as a power operator too."""
    expr = str(expression).replace("^", "**")
    tree = ast.parse(expr, mode="eval")
    result = _eval_node(tree.body)
    # Present clean integers without a trailing .0
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return result


# ---------------------------------------------------------------------------
# Linear-trend forecasting (the "predictive" showcase)
# ---------------------------------------------------------------------------
def forecast(values, periods=3):
    """Fit y = a + b*x by least squares and project the next `periods` values."""
    values = [float(v) for v in values]
    n = len(values)
    if n < 2:
        raise ValueError("Need at least two numbers to forecast a trend.")
    periods = max(1, int(periods or 3))

    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    slope = (
        sum((xs[i] - mean_x) * (values[i] - mean_y) for i in range(n)) / denom
        if denom
        else 0.0
    )
    intercept = mean_y - slope * mean_x
    predictions = [round(intercept + slope * (n + i), 3) for i in range(periods)]

    direction = "rising" if slope > 0 else "falling" if slope < 0 else "flat"
    return {
        "slope": round(slope, 4),
        "direction": direction,
        "predictions": predictions,
    }


# ---------------------------------------------------------------------------
# Dispatcher used by the agentic loop
# ---------------------------------------------------------------------------
def run_tool(name, tool_input):
    """Execute a tool by name and return a string result for the model."""
    try:
        if name == "calculator":
            value = calculate(tool_input.get("expression", ""))
            return f"Result: {value}"

        if name == "current_datetime":
            now_local = datetime.now().astimezone()
            now_utc = datetime.now(timezone.utc)
            return (
                f"Local time: {now_local.strftime('%A, %d %B %Y, %I:%M %p %Z')}\n"
                f"UTC time:   {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )

        if name == "forecast_trend":
            result = forecast(
                tool_input.get("values", []), tool_input.get("periods", 3)
            )
            preds = ", ".join(str(p) for p in result["predictions"])
            return (
                f"Trend is {result['direction']} (slope {result['slope']}). "
                f"Next {len(result['predictions'])} predicted value(s): {preds}"
            )

        return f"Unknown tool: {name}"
    except Exception as exc:  # return errors as tool output so the model can recover
        return f"Tool error: {exc}"


# ---------------------------------------------------------------------------
# Helpers for DEMO mode (no API key) so the UI still shows real tool results
# ---------------------------------------------------------------------------
def extract_numbers(text):
    """Pull out numbers from free text, e.g. '12, 15, 14' -> [12, 15, 14]."""
    import re

    return [float(m) for m in re.findall(r"-?\d+(?:\.\d+)?", text)]
