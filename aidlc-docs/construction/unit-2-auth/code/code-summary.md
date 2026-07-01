# 유닛 2: 인증 — 코드 생성 완료

## 결과

인증은 **외부 IdP(Cognito) 없이 소셜 OAuth를 직접 구현**하는 방식으로 배포됨. (`config.py`의 `auth_mode` 주석: "Cognito 제거됨 — 소셜 OAuth로 단일화")

- ✅ `services/auth_service.py` — Google/Kakao/Naver `PROVIDERS` 정의, `authorize_url` / `exchange_code` / `get_userinfo` (Authorization Code Grant 직접 구현), HS256 JWT `create_token` / `decode_token` (표준 라이브러리 hmac+base64, 만료 검증)
- ✅ `deps.py` — `get_current_user` seam: `Authorization: Bearer <JWT>` 검증(`auth_jwt_enabled`), 실패 시 401, 로컬은 demo 유저 폴백(`auth_mode=demo`)
- ✅ `routers/auth.py` — `/{provider}/login`, `/{provider}/callback`(code 교환 → 사용자 upsert → JWT 발급 → `bada://auth` 딥링크), `/kakao/link-code`, `/me`, `/logout`. `state`에 CSRF nonce + `return_to`를 실어 전달하고 `_safe_return_to` 화이트리스트로 오픈 리다이렉트 차단

> `models.User.cognito_sub` 컬럼은 레거시로 남아 있으나 현재 인증 경로에서는 사용하지 않는다.

## 배포 시 필요한 설정 (환경변수 / Secrets Manager)

```text
# 인증 모드
AUTH_MODE = "oauth"          # demo | oauth
AUTH_JWT_ENABLED = true

# 자체 발급 JWT
JWT_SECRET = <Secrets Manager>     # 운영에서 반드시 교체
JWT_EXPIRE_MINUTES = 10080         # 기본 7일
APP_BASE_URL = "https://badasoft.com"

# 소셜 OAuth provider별 자격증명 + redirect_uri
GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REDIRECT_URI
KAKAO_REST_API_KEY / KAKAO_CLIENT_SECRET / KAKAO_REDIRECT_URI
NAVER_CLIENT_ID / NAVER_CLIENT_SECRET / NAVER_REDIRECT_URI
```

각 provider 콘솔의 Redirect URI는 `https://api.badasoft.com/auth/{provider}/callback`와 일치해야 한다.

## 코드 변경 사항

**없음** — 소셜 OAuth 인증 코드가 이미 완성 상태. 운영 전환은 provider 자격증명과 JWT secret을 실제 값으로 주입하면 동작.

## 운영 참고

- 인증 상태는 stateless JWT라 서버 세션이 없다. 모바일 클라이언트는 API 401 응답 시 저장 토큰을 삭제하고 재로그인 흐름으로 이동한다(자동 로그아웃).
- Cognito 관련 Terraform 리소스는 인프라에 잔존하나 앱 인증 경로에서는 호출하지 않는다.
