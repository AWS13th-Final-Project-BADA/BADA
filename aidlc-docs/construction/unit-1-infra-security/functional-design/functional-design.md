# 유닛 1: 인프라 및 보안 — 기능 설계

## 설계 범위

유닛 1은 순수 인프라/보안 변경이므로 비즈니스 로직이 없습니다. 이 문서는 **보안 미들웨어의 동작 명세**를 정의합니다.

---

## 1. 보안 헤더 미들웨어

### 동작 규칙
모든 HTML 응답에 다음 헤더를 추가:

| 헤더 | 값 |
|------|-----|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://api.badasoft.com` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

### 적용 조건
- 모든 응답에 적용 (HTML뿐 아니라 API JSON 응답에도 X-Content-Type-Options, HSTS 적용)
- `/health`, `/version` 포함

---

## 2. CORS 도메인 제한

### 동작 규칙
- 허용 오리진: `https://badasoft.com`, `https://www.badasoft.com`
- 임시 허용: ALB DNS (도메인 DNS 전파 전)
- 허용 메서드: `GET, POST, PUT, PATCH, DELETE, OPTIONS`
- 허용 헤더: `Authorization, Content-Type`
- credentials: `true`

### 전환 전략
1. 초기 배포: ALB DNS + `https://badasoft.com` 모두 allow_origins에 포함
2. DNS 전파 완료 후: ALB DNS 제거

---

## 3. Rate Limiting

### 동작 규칙
- 대상: 모든 public endpoint
- 제한: **IP당 60요청/분** (인메모리 카운터, 단일 인스턴스)
- 초과 시: `429 Too Many Requests` 반환
- 헤더: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### 예외
- `/health`, `/version`: Rate limit 제외
- 내부 Worker → Backend 호출: 제외 (해당 없음, 2단계 전환으로 없어짐)

---

## 4. ALB HTTPS 라우팅

### 동작 규칙
- HTTP(80) → HTTPS(443) 리다이렉트
- 호스트 `api.bada.kr` → Backend Target Group
- 호스트 `bada.kr` → Frontend Target Group (유닛 5에서 생성)
- 기본(default) → Backend Target Group (도메인 설정 전 ALB DNS 접근용)

---

## 5. Worker 기동

### 동작 규칙
- `desired_count`: 0 → 1 전환
- 헬스체크: ECS 태스크 실행 상태 확인 (consumer.py 무한 루프 = healthy)
- 환경변수: `DATABASE_URL` (Secrets Manager), `SQS_QUEUE_URL`, `AWS_REGION`, `S3_BUCKET`

---

## 테스트 가능 속성 (PBT-01)

유닛 1에는 규칙 기반 비즈니스 로직이 없으므로 PBT 해당 없음 (N/A).
보안 미들웨어의 동작은 통합 테스트로 검증:
- 모든 응답에 보안 헤더 포함 확인
- 허용되지 않은 오리진의 CORS 차단 확인
- Rate limit 초과 시 429 반환 확인
