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
- **지금 챗봇**: 프론트 입력창 + `/chat/messages` + intent/risk/guardrail + mock/Bedrock 전환 구조.
- **아직 스텁**: 이미지 OCR(숫자는 직접 입력) = B2 bolt에서 Bedrock 연결.
  인증(Cognito)·S3 업로드·실시간 번역(Translate)도 AWS 모드(W1) 연결 후 동작.
- **DB 교체**: 나중에 Postgres로 바꾸려면 `backend/app/config.py`의 `database_url`만 변경
  (`postgresql+psycopg://...`) + `pip install "psycopg[binary]"`. 모델 코드는 그대로.

## 문제 해결

- `ModuleNotFoundError` → venv 활성화 확인, `pip install -r backend/requirements.txt` 다시.
- 포트 충돌 → `uvicorn app.main:app --reload --port 8001`.
- DB 초기화 → `backend/bada.db` 파일 삭제 후 재실행.
