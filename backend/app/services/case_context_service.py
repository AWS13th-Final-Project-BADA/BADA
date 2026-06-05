from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "sample_case_context.json"


def load_case_context(case_id: int) -> dict[str, Any] | None:
    if not DATA_FILE.exists():
        return None

    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

    case_key = str(case_id)
    return raw.get(case_key)
