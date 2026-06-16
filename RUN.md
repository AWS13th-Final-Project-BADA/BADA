# BADA 로컬 실행 (AWS 없이, Windows)

풀스택 앱을 PC에서 바로 띄웁니다. SQLite라 Docker도 필요 없어요.

## 1. 백엔드 + 프론트(한 번에) 실행

```powershell
cd "C:\Users\dy981\OneDrive\바탕 화면\BADA"
.venv\Scripts\Activate.ps1            # venv 활성화 (없으면: python -m venv .venv 먼저)
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload
```

## 2. 브라우저 열기

```
http://localhost:8000
```

프론트엔드가 백엔드에서 같이 서빙됩니다(별도 Node/빌드 불필요).

## 3. 써보기

1. **+ 새 사건** → 사업장·근무기간·시급 입력 → 사건 생성
2. **증거 추가** → 계약서/명세서/입금/대화 등 분류만 등록 (누락 안내에 반영됨)
3. **분석 입력**에서 **[데모 데이터 채우기]** 버튼 → **분석 실행**
4. 결과: 미지급 의심 금액, 공제표(확인 필요), 타임라인, GPS 교차검증, 누락 자료
5. **제출용 리포트 열기** → 새 탭에서 인쇄/ PDF 저장
6. **챗봇** → `/chat/messages` API를 통해 다음 준비 항목을 질문

> 우측 상단 **KO / VI / EN** 으로 UI 언어 전환.

## 4. AI 챗봇 모드

기본값은 AWS 없이 동작하는 `mock`입니다. 실제 LLM을 붙일 때는 `.env`에서 모드를 바꿉니다.

```bash
cd /c/Users/DGSO23/BADA/BADA/backend
cp ../.env.example .env
```

```dotenv
AI_CHAT_MODE=mock
```

Bedrock Claude를 호출하려면 AWS 자격 증명이 설정된 환경에서:

```dotenv
AI_CHAT_MODE=bedrock
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
AI_CHAT_MAX_TOKENS=700
```

서버 실행:

```bash
cd /c/Users/DGSO23/BADA/BADA/backend
source .venv/Scripts/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

`bedrock` 모드에서 호출이 실패하면 서버는 데모가 끊기지 않도록 mock 답변으로 fallback합니다.

## 동작 범위 / 한계

- **지금 되는 것**: 사건 관리, 규칙 기반 분석(차액·공제·누락·GPS 교차검증), 타임라인, 리포트.
- **OCR·AI 문장화·번역**: 기본은 Mock(키 불필요). `backend/.env`에 `PROVIDER_MODE=aws` +
  AWS 자격증명(`aws configure`)을 넣으면 실제 동작(Claude Vision/Bedrock/Translate). → `docs/enable-aws.md`
  - 위 `pip install -r backend/requirements.txt` 한 번이면 로컬·AWS 둘 다 커버(boto3·requests 포함).
- **AI 챗봇**: 프론트 입력창 + `/chat/messages` + intent/risk/guardrail + mock/Bedrock 전환 구조.
- **아직 스텁**: 인증(Cognito)·S3 업로드는 AWS 모드 연결 후 동작(다른 담당).
- **DB 교체**: 나중에 Postgres로 바꾸려면 `backend/app/config.py`의 `database_url`만 변경
  (`postgresql+psycopg://...`) + `pip install "psycopg[binary]"`. 모델 코드는 그대로.

## 문제 해결

- `ModuleNotFoundError` → venv 활성화 확인, `pip install -r backend/requirements.txt` 다시.
- 포트 충돌 → `uvicorn app.main:app --reload --port 8001`.
- DB 초기화 → `backend/bada.db` 파일 삭제 후 재실행.

## RDS Postgres + RAG 연결

RDS를 만든 뒤 `backend/.env`에 아래 값을 넣습니다.

```dotenv
DATABASE_URL=postgresql+psycopg://bada:PASSWORD@RDS_ENDPOINT:5432/bada
DATABASE_AUTO_CREATE=true
DATABASE_SSL_MODE=require
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

RAG_ENABLED=true
RAG_USE_VECTOR=true
EMBEDDING_MODE=bedrock
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
EMBEDDING_DIMENSION=1024
```

로컬에서 RDS에 붙으려면 RDS 보안 그룹 inbound에 현재 PC IP의 `5432` 접근이 열려 있어야 합니다.

DB 연결과 테이블 생성을 먼저 확인합니다.

```bash
cd /c/Users/DGSO23/BADA/BADA/backend
source .venv/Scripts/activate
pip install -r requirements.txt
python scripts/check_db.py
```

정상 예:

```text
connection=ok dialect=postgresql
create_all=ok
tables=analysis_results, cases, evidences, rag_chunks, rag_documents, ...
```

RAG seed를 적재합니다.

```bash
python scripts/ingest_rag_seed.py
```

정상 예:

```text
rag_ingest=ok documents=3 chunks=5
```

서버 실행 후 DB 헬스체크:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
curl http://127.0.0.1:8000/health/db
```
