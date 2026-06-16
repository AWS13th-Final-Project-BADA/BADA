from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.db import check_db_connection, engine, init_db  # noqa: E402


def _mask_url(url: str) -> str:
    if "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    return f"{scheme}://***:***@{rest.split('@', 1)[1]}"


def main() -> None:
    print(f"DATABASE_URL={_mask_url(settings.database_url)}")
    print(f"DATABASE_SSL_MODE={settings.database_ssl_mode or '(none)'}")
    print(f"DATABASE_AUTO_CREATE={settings.database_auto_create}")

    result = check_db_connection()
    print(f"connection=ok dialect={result['dialect']}")

    if settings.database_auto_create:
        init_db()
        print("create_all=ok")

    tables = inspect(engine).get_table_names()
    print("tables=" + ", ".join(sorted(tables)))


if __name__ == "__main__":
    main()
