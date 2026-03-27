"""
Shared configuration for LLM Eval Judge.
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = BASE_DIR / "prompts"
DATA_FILE = DATA_DIR / "eval_data.json"
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 2048
