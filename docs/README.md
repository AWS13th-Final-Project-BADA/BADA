# BADA 문서 목차

## architecture/ — 시스템 설계 & 기능 상세

| 문서 | 내용 |
|------|------|
| [ocr.md](architecture/ocr.md) | OCR 파이프라인 + 규칙 엔진 전체 아키텍처 |
| [speech-to-text.md](architecture/speech-to-text.md) | Amazon Transcribe 음성 전사 + 화자 분리 |
| [translation.md](architecture/translation.md) | 다국어 번역 (Amazon Translate + Claude 피벗) |
| [agent-feature-brief.md](architecture/agent-feature-brief.md) | 증거 수집 에이전트 (4단계 자동 분류) |
| [gps-feature-brief.md](architecture/gps-feature-brief.md) | GPS 지오펜스 + 출퇴근 교차검증 |

## infra/ — 인프라 설계 & 현황

| 문서 | 내용 |
|------|------|
| [implementation-status.md](infra/implementation-status.md) | 현재 배포된 인프라 전체 현황 (마스터 문서) |
| [production-roadmap.md](infra/production-roadmap.md) | MVP → 프로덕션 전환 5단계 로드맵 |
| [high-availability-design.md](infra/high-availability-design.md) | HA 설계 (Auto Scaling, Multi-AZ, DR) |
| [terraform-refactoring.md](infra/terraform-refactoring.md) | Terraform 서비스별 state 분리 설계 |
| [security-operations-plan.md](infra/security-operations-plan.md) | ECR 스캔, Task Role 분리, 비용 현황 |
| [verification-0625.md](infra/verification-0625.md) | 6/25 인프라 검증 + 팀별 요청사항 |
| [enable-aws.md](infra/enable-aws.md) | 로컬→AWS 모드 전환 가이드 |
| [iam-bedrock-policy.json](infra/iam-bedrock-policy.json) | Bedrock/Translate IAM 정책 참조 |
| [architecture.drawio](infra/architecture.drawio) | 인프라 아키텍처 다이어그램 (draw.io) |

## operations/ — 운영 & 모니터링

| 문서 | 내용 |
|------|------|
| [monitoring-guide.md](operations/monitoring-guide.md) | Prometheus + Grafana 인계 + Alert 테스트 절차 |
| [ownership.md](operations/ownership.md) | 팀 역할 분담 (초기 7역할 기준) |

## mobile/ — 모바일 앱

| 문서 | 내용 |
|------|------|
| [e2e-test.md](mobile/e2e-test.md) | 모바일 E2E 테스트 리포트 (로그인→분석→PDF) |

## decisions/ — 의사결정 기록 (ADR)

| 문서 | 내용 |
|------|------|
| [decision-record-20260625.md](decisions/decision-record-20260625.md) | 프로덕션 고도화 20건 의사결정 |
| [privacy-legal-requirements.md](decisions/privacy-legal-requirements.md) | 개인정보보호법 + 위치정보법 준수 요건 |

## runbooks/ — 장애 대응 절차

| 문서 | 내용 |
|------|------|
| [demo-incident-response.md](runbooks/demo-incident-response.md) | 데모 중 장애 진단 (로그인→업로드→분석→PDF) |
| [rollback-and-recovery.md](runbooks/rollback-and-recovery.md) | ECS 롤백 + 서비스 복구 |
| [rds-recovery.md](runbooks/rds-recovery.md) | RDS 스냅샷 복원 + 암호화 전환 |
| [project-closure.md](runbooks/project-closure.md) | 7/10 프로젝트 종료 + 리소스 정리 |

## troubleshooting/ — 트러블슈팅

| 문서 | 내용 |
|------|------|
| [transcribe-deploy-issues.md](troubleshooting/transcribe-deploy-issues.md) | Transcribe 배포 이슈 해결 |
| [timeline-confidence-type.md](troubleshooting/timeline-confidence-type.md) | 타임라인 confidence 타입 이슈 |
