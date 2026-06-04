"""백엔드 테스트 공통 픽스처. 각 기능 담당자는 이 client 픽스처로 API 테스트를 추가한다."""
import os

# 테스트는 격리된 SQLite 사용 (app import 전에 설정)
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client():
    from app.main import app
    from app.db import Base, engine
    # 매 테스트 깨끗한 스키마 (파일 삭제 대신 drop/create — 커넥션 풀 안전)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c
