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

> 우측 상단 **KO / VI / EN** 으로 UI 언어 전환.

## 동작 범위 / 한계

- **지금 되는 것**: 사건 관리, 규칙 기반 분석(차액·공제·누락·GPS 교차검증), 타임라인, 리포트.
- **OCR·AI 문장화·번역**: 기본은 Mock(키 불필요). `backend/.env`에 `PROVIDER_MODE=aws` +
  AWS 자격증명(`aws configure`)을 넣으면 실제 동작(Claude Vision/Bedrock/Translate). → `docs/enable-aws.md`
  - 위 `pip install -r backend/requirements.txt` 한 번이면 로컬·AWS 둘 다 커버(boto3·requests 포함).
- **아직 스텁**: 인증(Cognito)·S3 업로드는 AWS 모드 연결 후 동작(다른 담당).
- **DB 교체**: 나중에 Postgres로 바꾸려면 `backend/app/config.py`의 `database_url`만 변경
  (`postgresql+psycopg://...`) + `pip install "psycopg[binary]"`. 모델 코드는 그대로.

## 문제 해결

- `ModuleNotFoundError` → venv 활성화 확인, `pip install -r backend/requirements.txt` 다시.
- 포트 충돌 → `uvicorn app.main:app --reload --port 8001`.
- DB 초기화 → `backend/bada.db` 파일 삭제 후 재실행.
