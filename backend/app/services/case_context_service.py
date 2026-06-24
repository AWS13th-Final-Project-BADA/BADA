from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "sample_case_context.json"


def load_case_context(case_id: str | None) -> dict[str, Any] | None:
    if not case_id:
        return None

    if not DATA_FILE.exists():
        return None

    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

    return raw.get(str(case_id))
