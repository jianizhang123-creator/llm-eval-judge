"""
Base utilities shared by all agents: Claude API calls, JSON parsing, and
prompt loading from markdown files.
"""

import json
import re
import time

from anthropic import Anthropic

from config import MODEL, MAX_TOKENS, PROMPTS_DIR

client = Anthropic()


def load_prompt(agent_name: str) -> str:
    """Load a system prompt from ``prompts/<agent_name>.md``."""
    path = PROMPTS_DIR / f"{agent_name}.md"
    return path.read_text(encoding="utf-8")


def parse_json_response(text: str) -> dict | None:
    """Multi-strategy JSON extraction from LLM output."""
    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: strip markdown code fences
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: find first { ... } block
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass

    # Strategy 4: aggressive cleanup — remove trailing commas
    cleaned = text.strip()
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        print(f"[parse_json] ALL strategies failed. Raw text:\n{text[:500]}")
        return None


def call_agent(agent_name: str, system_prompt: str, user_prompt: str,
               max_retries: int = 3) -> dict | None:
    """Call Claude API with retry and return parsed JSON."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return parse_json_response(resp.content[0].text)
        except Exception as exc:
            print(f"[{agent_name}] attempt {attempt} failed: {exc}")
            if attempt < max_retries:
                time.sleep(1)
    return None
