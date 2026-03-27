"""
Persistent data store — load / save eval_data.json which holds both
sample definitions and the accumulated error knowledge base.
"""

import json

from config import DATA_FILE

DEFAULT_DATA = {
    "samples": [],
    "knowledge_base": {
        "errors": [],
        "patterns": [],
        "stats": {
            "total_evaluated": 0,
            "preference_count": 0,
            "error_count": 0,
            "ambiguous_count": 0,
            "accuracy_by_field": {
                "amount": 1.0, "category": 1.0,
                "date": 1.0, "merchant": 1.0,
            },
            "error_type_distribution": {},
            "hallucination_rate": 0.0,
        },
    },
}


def load_data() -> dict:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return json.loads(json.dumps(DEFAULT_DATA))


def save_data(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
