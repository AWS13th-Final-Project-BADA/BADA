# 유닛 1: 인프라 및 보안 — 비기능 요구사항

## Security Baseline 적용 항목

| 규칙 ID | 적용 여부 | 유닛 1 조치 |
|---------|----------|------------|
| SECURITY-01 | 적용 | ACM HTTPS, RDS TLS(기존), S3 KMS(기존) |
| SECURITY-02 | 적용 | ALB access logging 활성화 |
| SECURITY-03 | 적용 | 기존 CloudWatch 로깅 유지 (변경 없음) |
| SECURITY-04 | 적용 | 보안 헤더 미들웨어 추가 |
| SECURITY-05 | N/A | 유닛 1에서 API 입력 변경 없음 |
| SECURITY-06 | 적용 | IAM 정책 검토 (와일드카드 확인) |
| SECURITY-07 | 적용 | Security Group 검토 (443만 public) |
| SECURITY-08 | 적용 | CORS 도메인 제한 |
| SECURITY-09 | 적용 | JWT 기본값 제거 (Secrets Manager 주입 확인) |
| SECURITY-10 | N/A | 의존성 변경 없음 |
| SECURITY-11 | 적용 | Rate limiting 추가 |
| SECURITY-12 | N/A | 인증은 유닛 2 |
| SECURITY-13 | N/A | 소프트웨어 무결성은 기존 CI 유지 |
| SECURITY-14 | 적용 | ALB access log + 기존 CloudWatch Alarm |
| SECURITY-15 | N/A | 예외 처리는 기존 코드 유지 |

## Resiliency Baseline 적용 항목

| 항목 | 조치 |
|------|------|
| Health Check | ECS 태스크 health check 유지 (Backend /health, Worker 프로세스 alive) |
| 자동 복구 | ECS 서비스가 unhealthy 태스크 자동 교체 |
| DLQ | SQS DLQ 기존 구성 유지 |
| Alarm | 기존 8개 CloudWatch Alarm 유지 |

## 기술 스택 결정

| 항목 | 선택 | 근거 |
|------|------|------|
| Rate Limiter | 인메모리 (단일 인스턴스) | Redis 불필요, ECS 1 task |
| HTTPS | ACM 공개 인증서 + ALB | 무료, 자동 갱신 |
| ALB 로깅 | S3 버킷 저장 | SECURITY-02 준수 |
| 보안 헤더 | FastAPI Middleware | 프레임워크 내장, 간단 |
