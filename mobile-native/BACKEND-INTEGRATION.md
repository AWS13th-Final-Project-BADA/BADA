# 모바일(mobile-native) ↔ 백엔드 연계 인계서

> 대상: 백엔드 담당. 네이티브 앱이 **완전한 end-to-end로 동작**하려면 아래 3건의 소규모 백엔드 변경이 필요하다.
> 원칙: **셋 다 "추가(additive)·게이트" 방식 — 기존 웹 동작은 바이트 단위로 그대로 유지**된다(웹 무영향).
> 앱은 이 3건 없이도 데모 가능(개발용 토큰 주입 / report.html / 일반 챗봇)하지만, 정식 연동엔 필요하다.

작성 기준: `develop` 코드 · 모바일 브랜치 `feature/mobile-native`.

---

## 1. 인증 딥링크 (로그인 토큰을 앱으로 반환)

### 현재 동작
- `backend/app/routers/auth.py`
  - `cognito_callback` (L38–63): 로그인 성공 후 `return RedirectResponse(f"{app_base_url}/#token={token}")`
  - `social_callback` (L85–103): 동일하게 `…/#token={jwt}`
- 즉 토큰을 **웹 주소의 URL 해시(`#token=`)** 로 던진다. 앱(WebBrowser 세션)은 이 해시를 못 받는다.

### 모바일이 기대하는 것
- 앱은 시스템 브라우저로 로그인 URL을 열고 **앱 스킴 딥링크 `bada://auth?token=<JWT>`** 로 토큰을 돌려받는다.
- 클라이언트는 이미 구현됨: `mobile-native/src/lib/auth.ts` 가 `redirect_uri=bada://auth` 를 쿼리로 보낸다.

### 필요 변경 (최소)
1. `cognito_login` / `social_login` 이 쿼리 `redirect_uri` 를 받아 **OAuth `state` 에 실어** 전달.
2. 콜백에서 `state` 의 `redirect_uri` 가 앱 스킴(`bada://`)이면 해시 대신 **쿼리로 302**:
   ```python
   # cognito_callback / social_callback 끝부분
   if app_redirect and app_redirect.startswith("bada://"):
       return RedirectResponse(f"{app_redirect}?token={token}")
   return RedirectResponse(f"{app_base_url}/#token={token}")  # 기존 웹 흐름(그대로)
   ```
3. Cognito App Client 의 **Allowed Callback URLs 는 변경 불필요**(콜백은 여전히 `api.badasoft.com/auth/.../callback`). 앱 스킴 리다이렉트는 그 콜백 내부에서 일어남.

### 검증
- 앱에서 "이메일 로그인" → 브라우저 → 로그인 → 앱으로 복귀하며 토큰 저장 → 보호 API(`GET /cases`) 200.
- 웹 로그인은 동일하게 `#token=` 로 동작(회귀 없음).

### 영향
- 웹: 무영향(앱 스킴이 아닐 때 기존 분기). 모바일: 로그인 완성.

---

## 2. 챗봇 `case_id` 타입 정합 (UUID 허용)

### 현재 동작
- `backend/app/schemas_ai_chat.py` (L15–19): `ChatMessageRequest.case_id: int = Field(..., example=1)`
- 그러나 사건 id는 **UUID 문자열**(`models.Case.id = String(36)`). 타입 불일치.

### 모바일이 보내는 것
- `mobile-native/app/chat.tsx`: 일반 상담은 `case_id: 0`, 사건 맥락 진입 시 사건 id를 보내려 하나 UUID라 현재는 `0` 으로 폴백.

### 필요 변경 (최소)
- `case_id` 를 **문자열(UUID) 수용**으로:
  ```python
  case_id: str | None = None   # 또는 Union[int, str]; 없으면 일반 상담
  ```
- 오케스트레이터(`services/ai_chat_orchestrator.py`)에서 `case_id` 로 사건 조회 시 문자열 키로 `db.get(Case, case_id)` 사용. 없거나 None이면 `used_case_context=False` 로 일반 상담(현행 동작 유지).

### 검증
- 사건 상세 → AI 상담 진입 → 그 사건 맥락(금액/기간)을 반영한 답변, `used_case_context=true`.
- `case_id` 없이도 일반 상담 정상.

### 영향
- 기존 호출(정수/None)도 수용하도록 `Union` 또는 옵셔널로 두면 회귀 없음.

---

## 3. Evidence Pack PDF 다운로드 엔드포인트

### 현재 동작
- 제출용 리포트는 `GET /cases/{case_id}/report.html` (`analysis.py` L110) — HTML만 존재.
- 워커가 PDF를 S3에 저장하고 키를 보관: `models.py` L212 `pdf_ko_s3_key`. 그러나 **이를 내려주는 라우트가 없음.**
- S3 presign 유틸은 있음: `services/s3.py` L29 `presign_get(file_key, expires)`.

### 모바일이 기대하는 것
- `mobile-native/app/cases/analysis.tsx` 는 현재 report.html 을 앱 내 브라우저로 연다.
- 진짜 PDF 다운로드를 원하면 `GET /cases/{case_id}/report.pdf` 가 필요.

### 필요 변경 (최소, 신규 라우트 1개)
```python
@router.get("/report.pdf")
def report_pdf(case_id: str, db: Session = Depends(get_db)):
    rep = _latest_report(case_id, db)          # pdf_ko_s3_key 보유 레코드
    if not rep or not rep.pdf_ko_s3_key:
        raise HTTPException(404, "pdf not ready")
    return RedirectResponse(s3.presign_get(rep.pdf_ko_s3_key, expires=300))
```
- 키가 아직 없으면 404 → 앱은 report.html 폴백(현행).

### 검증
- 분석 완료 + PDF 생성된 사건에서 `report.pdf` → presigned S3 URL 302 → PDF 다운로드.

### 영향
- 순수 신규 엔드포인트. 기존 무영향.

---

## 우선순위 제안
1. **인증 딥링크(§1)** — 이게 없으면 앱 실사용 로그인 불가(최우선).
2. **챗봇 case_id(§2)** — 사건 맥락 상담 품질.
3. **report.pdf(§3)** — report.html 폴백이 있어 후순위.

## 연락/참조
- 모바일 코드: `mobile-native/` (`src/lib/auth.ts`, `app/chat.tsx`, `app/cases/analysis.tsx`)
- 전환 배경·설계: `aidlc-docs/construction/mobile/mobile-setup.md`
