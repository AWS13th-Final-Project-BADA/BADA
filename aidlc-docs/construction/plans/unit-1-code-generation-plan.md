# 유닛 1: 인프라 및 보안 — 코드 생성 계획

## 실행 단계

- [x] 1. Terraform: ALB Security Group에 443 포트 추가
- [x] 2. Terraform: ACM 인증서 + Route 53 DNS 검증 레코드
- [x] 3. Terraform: HTTPS listener (443) + HTTP→HTTPS 리다이렉트
- [x] 4. Terraform: Route 53 A 레코드 (badasoft.com, api.badasoft.com → ALB)
- [x] 5. Terraform: 호스트 기반 라우팅 규칙
- [x] 6. Terraform: ALB access logging (S3 버킷)
- [x] 7. Terraform: Frontend ECR + Target Group (유닛 5 준비)
- [x] 8. Terraform: variables.tf에 도메인 변수 추가
- [x] 9. Terraform: Worker desired_count = 1 (tfvars에서 변경)
- [x] 10. Backend: 보안 헤더 미들웨어 (backend/app/middleware/__init__.py)
- [x] 11. Backend: Rate limit 미들웨어 (backend/app/middleware/rate_limit.py)
- [x] 12. Backend: main.py CORS 도메인 제한 + 미들웨어 등록
- [x] 13. 검증: terraform fmt ✅ + Backend 47 tests passed ✅ + Worker 155 tests passed ✅
