"""Claude-powered trade decision engine.

Builds the daily prompt, calls the Claude API (Opus 4.8 with adaptive
thinking), and parses the JSON decision. On any failure the caller receives a
safe HOLD decision so the portfolio is never corrupted by a bad/empty response.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import anthropic

from utils import log, log_error

MODEL = "claude-opus-4-8"
MAX_TOKENS = 16000

SYSTEM_PROMPT = (
    "You are an elite autonomous trading agent managing $100K for maximum "
    "30-day returns. You have full discretion over every decision — what to "
    "buy, what to sell, how much, when. You are not conservative. You chase "
    "asymmetric opportunities. You think in catalysts, momentum, and "
    "conviction.\n\n"
    "Rules:\n"
    "- Maximum 5 positions at any time\n"
    "- Minimum position size 10% of portfolio\n"
    "- You must give a reason for every trade\n"
    "- You can go 100% cash if you see no opportunity\n"
    "- You can concentrate heavily if conviction is high\n"
    "- Always output valid JSON"
)

OUTPUT_SHAPE = """{
  "market_assessment": "1-2 sentence read on today's market",
  "trades": [
    {
      "action": "BUY or SELL or HOLD",
      "asset": "ticker",
      "quantity": number,
      "price": number,
      "dollar_amount": number,
      "conviction": "HIGH/MEDIUM/LOW",
      "catalyst": "why now"
    }
  ],
  "updated_portfolio": {
    "cash": number,
    "positions": {},
    "total_value": number
  },
  "daily_pnl": number,
  "cumulative_pnl": number,
  "reasoning": "full explanation of today's thinking"
}"""


def _build_user_prompt(
    today: str,
    portfolio: Dict[str, Any],
    prices: Dict[str, Any],
    headlines: List[str],
    yesterday_decision: Optional[Dict[str, Any]],
) -> str:
    headlines_block = "\n".join(f"- {h}" for h in headlines) or "- (none available)"
    yesterday_block = (
        json.dumps(yesterday_decision, indent=2)
        if yesterday_decision
        else "(no prior decision — this is day one)"
    )
    return (
        f"Date: {today}\n"
        f"Portfolio: {json.dumps(portfolio, indent=2)}\n"
        f"Current prices: {json.dumps(prices, indent=2)}\n"
        f"Recent news headlines:\n{headlines_block}\n"
        f"Yesterday's decision: {yesterday_block}\n\n"
        "Analyze the market today. What is your trade decision?\n\n"
        f"Output ONLY this JSON:\n{OUTPUT_SHAPE}"
    )


def _extract_json(text: str) -> Dict[str, Any]:
    """Pull the first balanced JSON object out of a text blob."""
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response")

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("Unbalanced JSON object in model response")


def _hold_decision(reason: str) -> Dict[str, Any]:
    """A safe no-op decision used whenever the API call/parse fails."""
    return {
        "market_assessment": "Decision engine unavailable — holding all positions.",
        "trades": [],
        "updated_portfolio": None,  # signal: caller keeps existing portfolio
        "daily_pnl": 0,
        "cumulative_pnl": None,
        "reasoning": f"HOLD (no action taken). {reason}",
        "_engine_error": True,
    }


def get_trade_decision(
    today: str,
    portfolio: Dict[str, Any],
    prices: Dict[str, Any],
    headlines: List[str],
    yesterday_decision: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Call Claude for today's decision. Returns a HOLD decision on failure."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return _hold_decision("ANTHROPIC_API_KEY is not set.")

    user_prompt = _build_user_prompt(
        today, portfolio, prices, headlines, yesterday_decision
    )

    client = anthropic.Anthropic(api_key=api_key)

    # The SDK already retries 429/5xx/network errors (max_retries default 2);
    # we add one more layer so transient failures don't force a HOLD.
    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                thinking={"type": "adaptive"},
                output_config={"effort": "high"},
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            if response.stop_reason == "refusal":
                return _hold_decision("Claude declined the request (refusal).")

            text = "".join(
                block.text for block in response.content
                if getattr(block, "type", None) == "text"
            )
            if not text.strip():
                raise ValueError("Empty text response from Claude")

            decision = _extract_json(text)
            log.info("Claude decision parsed: %d trade(s)",
                     len(decision.get("trades", [])))
            return decision

        except anthropic.APIStatusError as exc:
            last_exc = exc
            log.warning("Claude API error (attempt %d/3): %s", attempt, exc)
        except Exception as exc:  # noqa: BLE001 - parse / unexpected
            last_exc = exc
            log.warning("Decision parse error (attempt %d/3): %s", attempt, exc)

    log_error("Claude decision failed after 3 attempts — holding positions", last_exc)
    return _hold_decision(f"API/parse failure: {last_exc}")
