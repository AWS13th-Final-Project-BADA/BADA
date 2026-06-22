# 빌드 및 테스트 요약

## 배포 순서

```
1. terraform apply (HTTPS, Route 53, Worker 기동, ALB 로깅)
2. Backend 배포 (보안 미들웨어, Cognito 설정)
3. Worker 배포 (DB 직접, STT, PDF)
4. terraform apply (frontend_enabled = true)
5. Frontend 배포 (Next.js ECS)
6. 통합 검증
```

## 테스트 결과 요약

| 구분 | 테스트 수 | 상태 |
|------|----------|------|
| Backend 단위 | 47 | ✅ 통과 |
| Worker 단위 | 155 | ✅ 통과 |
| Worker PBT | 13 | ✅ 통과 |
| **합계** | **215** | ✅ |

## 배포 후 검증 체크리스트

### P0 (반드시 확인)
- [ ] `https://api.badasoft.com/health` → 200
- [ ] `https://badasoft.com` → Frontend 렌더
- [ ] Cognito 로그인 → 토큰 발급 → API 호출 성공
- [ ] SQS → Worker 분석 → DB 저장 → status=completed
- [ ] 보안 헤더 응답 확인
- [ ] CORS 허용/거부 정상

### P1 (데모 전 확인)
- [ ] 증거 업로드 → OCR → 엔티티 추출
- [ ] 전체 분석 → 타임라인 + 차액 + 번역
- [ ] PDF 생성 → S3 저장 → 다운로드
- [ ] 음성 전사 → Evidence.ocr_text 저장
- [ ] 카카오톡 봇 /skill 엔드포인트 동작
- [ ] 커뮤니티 게시판 CRUD

### P2 (품질)
- [ ] PBT CI 실행 + 시드 기록
- [ ] CloudWatch Alarm 정상 수신
- [ ] Rate limit 429 반환 확인

## 롤백 계획

| 컴포넌트 | 롤백 방법 |
|----------|----------|
| Backend | `.github/workflows/rollback-dev-backend.yml` 수동 실행 (이전 Task Definition) |
| Worker | Terraform `worker_desired_count = 0` 또는 이전 Task Definition |
| Frontend | 이전 이미지로 ECS 롤백 또는 `frontend_enabled = false` |
| Infra | `terraform plan` 확인 후 이전 상태로 revert |

## 비용 예상 (월)

| 리소스 | 예상 비용 |
|--------|----------|
| ECS Fargate (3 tasks: BE + WK + FE) | ~$45 |
| RDS PostgreSQL (db.t4g.micro) | ~$15 |
| ALB | ~$20 |
| S3 + KMS | ~$3 |
| SQS | ~$1 |
| Route 53 | ~$1 |
| Bedrock Claude (데모 사용량) | ~$10-30 |
| **합계** | **~$95-115/월** |

5주 운영 시 총 ~$150-180 예상 (1,500달러 예산 내 충분).
