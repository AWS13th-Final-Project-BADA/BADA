# 유닛 2: 인증 — 코드 생성 완료

## 결과

인증 코드가 **이미 완전히 구현되어 있음**을 확인:

- ✅ `cognito_auth_service.py` — JWKS RS256 토큰 검증, code 교환, 사용자 생성/동기화
- ✅ `auth_service.py` — 카카오/구글/네이버 OAuth + JWT 발급
- ✅ `deps.py` — `auth_mode=cognito` 분기 + Bearer 토큰 검증
- ✅ `routers/auth.py` — Cognito/소셜 login/callback/logout 엔드포인트

## 배포 시 필요한 설정 변경 (terraform.tfvars)

```hcl
# Cognito callback/logout URL에 HTTPS 도메인 추가
cognito_callback_urls = [
  "http://localhost:8000/auth/cognito/callback",
  "https://api.badasoft.com/auth/cognito/callback"
]
cognito_logout_urls = [
  "http://localhost:8000/",
  "https://badasoft.com/"
]

# Backend 환경변수 (ECS Task Definition에서 주입)
# AUTH_MODE = "cognito"  (또는 "oauth" for 소셜 직접)
# COGNITO_REDIRECT_URI = "https://api.badasoft.com/auth/cognito/callback"
# COGNITO_LOGOUT_URI = "https://badasoft.com/"
# APP_BASE_URL = "https://badasoft.com"
```

## 코드 변경 사항

**없음** — 기존 코드가 이미 완성 상태. 설정(환경변수/tfvars)만 전환하면 동작.

## 전환 순서

1. `terraform.tfvars` 에 HTTPS callback URL 추가 → `terraform apply`
2. ECS Task Definition 환경변수: `AUTH_MODE=cognito`, `APP_BASE_URL=https://badasoft.com`
3. Frontend(유닛 5)에서 Cognito Access Token으로 API 호출 구현
