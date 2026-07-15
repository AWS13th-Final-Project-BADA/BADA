"""백엔드 테스트 공통 픽스처. 각 기능 담당자는 이 client 픽스처로 API 테스트를 추가한다."""
import os

# 테스트는 격리된 SQLite + 결정적 local(Mock) 모드 (AWS 호출 없이 재현 가능)
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["PROVIDER_MODE"] = "local"
os.environ["AUTH_MODE"] = "demo"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client():
    from app.main import app
    from app.db import Base, engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c
