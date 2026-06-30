# BADA CI/CD 파이프라인 가이드

> 기준: 2026-06-26, 팀 레포 `develop` 브랜치
> 목적: BADA 팀 프로젝트에서 GitHub Actions가 어떤 기준으로 테스트, 빌드, 배포, Terraform 검증, 롤백을 수행하는지 빠르게 이해하기 위한 팀 공용 문서

## 1. 개요

BADA의 CI/CD는 세 갈래로 나뉜다.

1. 애플리케이션 코드 검증 및 배포
   - Backend, Worker 변경 시 테스트 후 ECS Fargate에 자동 배포
2. 인프라 코드 검증
   - Terraform 변경 시 PR에서 `plan` 자동 실행
   - 실제 `apply`는 인프라 담당자가 수동 수행
3. 모바일 앱 빌드 제출
   - `mobile-native/` 변경 시 Expo EAS Build로 Android 빌드 제출

핵심 원칙은 이렇다.

- 코드 배포는 빠르게 자동화한다.
- 인프라 변경은 영향 범위가 커서 사람이 검토한다.
- 모바일 빌드는 GitHub Actions가 제출까지만 맡고, 실제 결과물은 Expo에서 확인한다.

## 2. 전체 흐름

```text
PR 생성
  -> ci.yml
     - Ruff lint
     - Bandit SAST
     - pytest + coverage + eval
  -> terraform-plan.yml
     - infra/** 변경 PR일 때만 fmt / validate / plan
     - PR 코멘트에 결과 게시

develop merge 후
  -> deploy-dev.yml
     - Backend 이미지 빌드 / ECR push / ECS 배포 / HTTPS health check
  -> deploy-dev-worker.yml
     - Worker 이미지 빌드 / ECR push / ECS 배포 / service stable 확인
  -> build-mobile.yml
     - mobile-native 변경 시 Android EAS Build 제출

문제 발생 시
  -> rollback-dev-backend.yml
     - Backend만 GitHub Actions 수동 롤백
  -> Worker / Grafana
     - AWS CLI 또는 콘솔 수동 롤백
```

## 3. 현재 운영 중인 Workflow

| Workflow | 파일 | 역할 | 자동 실행 시점 |
| --- | --- | --- | --- |
| CI | `.github/workflows/ci.yml` | 코드 품질, 보안, 테스트 검증 | `main`, `develop` push / PR |
| Backend CD | `.github/workflows/deploy-dev.yml` | Backend 이미지 빌드 후 ECS 배포 | `develop`에 Backend/Worker 관련 변경 merge |
| Worker CD | `.github/workflows/deploy-dev-worker.yml` | Worker 이미지 빌드 후 ECS 배포 | `develop`에 Worker 변경 merge |
| Mobile Build | `.github/workflows/build-mobile.yml` | Android EAS Build 제출 | `develop`에 `mobile-native/**` 변경 merge 또는 수동 실행 |
| Terraform Plan | `.github/workflows/terraform-plan.yml` | Terraform 변경 PR에서 plan 결과 코멘트 | `infra/**` 변경 PR |
| Backend Rollback | `.github/workflows/rollback-dev-backend.yml` | Backend ECS Task Definition 수동 롤백 | 수동 실행 |

미구현 항목:

- Worker 전용 GitHub Actions 롤백 workflow
- Terraform apply 자동화

## 4. CI

파일: `.github/workflows/ci.yml`

실행 Job:

| Job | 도구 | 대상 | 의미 |
| --- | --- | --- | --- |
| Ruff Lint | `ruff 0.11.12` | `backend/`, `worker/` | Python 코드 스타일, 문법 검사 |
| Bandit SAST | `bandit 1.8.3` | `backend/app`, `worker/` | 보안 취약 패턴 검사 |
| Tests + Coverage | `pytest`, `pytest-cov` | Backend, Worker, Eval | 회귀 방지, 커버리지 30% 이상 |

주의:

- Ruff는 `--exit-zero`라서 경고가 있어도 CI를 실패시키지 않는다.
- Bandit, pytest는 실패 시 CI도 실패한다.

## 5. Backend CD

파일: `.github/workflows/deploy-dev.yml`

주요 동작:

```text
develop merge
  -> OIDC로 AWS 배포 Role Assume
  -> Docker Buildx / QEMU
  -> backend/Dockerfile 기준 ARM64 이미지 빌드
  -> ECR push
  -> 현재 ECS Task Definition 조회
  -> backend 컨테이너 image만 교체
  -> 새 revision 등록
  -> ECS service update
  -> services-stable 대기
  -> https://api.badasoft.com/health 200 확인
```

설계 이유:

- Terraform은 CPU, 메모리, Secret, IAM, 로그 설정 같은 "형태"를 관리
- GitHub Actions는 container image URI 같은 "내용"만 바꾼다
- 그래서 배포 자동화와 Terraform이 서로 덮어쓰지 않는다

참고:

- 현재 `worker/**` 변경에도 Backend CD가 실행된다
- 공통 빌드 컨텍스트와 API-Worker 결합도를 고려한 보수적 설정이다
- 장기적으로는 trigger 범위를 더 좁힐 수 있다

## 6. Worker CD

파일: `.github/workflows/deploy-dev-worker.yml`

주요 동작:

```text
develop merge
  -> OIDC로 AWS 배포 Role Assume
  -> worker/Dockerfile 기준 ARM64 이미지 빌드
  -> ECR push
  -> 현재 Worker Task Definition 조회
  -> worker 컨테이너 image만 교체
  -> 새 revision 등록
  -> ECS service update
  -> services-stable 대기
  -> desired/running/taskDefinition 상태 출력
```

Backend와 차이:

- Worker는 ALB 뒤 HTTP endpoint가 없다
- 그래서 GitHub Actions에서는 `services-stable`까지만 보고
- 실제 운영 검증은 CloudWatch Logs, SQS 적체, DLQ 증가 여부까지 확인해야 한다

## 7. 모바일 앱 빌드

파일: `.github/workflows/build-mobile.yml`

핵심 정보:

| 항목 | 값 |
| --- | --- |
| 트리거 | **`workflow_dispatch`(수동 실행) 전용** — push 자동 빌드 제거됨 |
| 실행 권한 | Write 권한 이상이면 누구나 Actions에서 Run workflow 가능 |
| 런타임 | Node.js 20 |
| 패키지 설치 | `npm ci` |
| 인증 | `EXPO_TOKEN` GitHub Secret |
| 빌드 방식 | Expo EAS Build |
| 기본 프로필 | `preview` |
| 수동 선택 | `preview`, `production` |
| 결과 처리 | 빌드 완료까지 대기 후 결과(JSON)에서 빌드 URL 추출 → Discord 알림 |

실행 흐름:

```text
GitHub → Actions → "Build Mobile (EAS Preview)" → Run workflow (수동)
  -> Checkout
  -> Node.js 20 + npm ci
  -> expo/expo-github-action@v8
  -> profile 결정 (입력값, 기본 preview)
  -> eas build --platform android --profile <preview|production> --non-interactive   # 이때 1회 차감
  -> 빌드 완료 대기 → 빌드 URL 추출 → Discord 알림
```

중요한 점:

- 이 workflow는 AWS 인프라를 변경하지 않는다
- **EAS 무료 빌드는 월 15회 한도**이므로, push 자동 빌드를 제거하고 **수동 실행 전용**으로 두어 쿼터 소진을 막는다
- **Run workflow를 누른 경우에만 `eas build`가 제출되어 1회 차감된다** (안 누르면 차감 0)
- 빌드하려면: **Actions → "Build Mobile (EAS Preview)" → Run workflow** (브랜치/프로필 선택)
- 팀 공유 권장: "빌드는 필요할 때만 수동 실행 (월 15회 한도)"
- GitHub Actions 성공 기준은 "Expo Build 제출 성공"이다
- 실제 APK/AAB 생성 여부는 Expo 대시보드에서 확인해야 한다
- (향후 승인 통제가 필요하면 `eas-build` Environment + Required reviewers로 전환 가능 — repo Admin 권한 필요)

## 8. Terraform Plan-in-PR

파일: `.github/workflows/terraform-plan.yml`

주요 동작:

```text
infra/** 변경 PR
  -> OIDC로 읽기 전용 plan Role Assume
  -> terraform fmt -check
  -> terraform init
  -> terraform validate
  -> terraform plan -lock=false
  -> PR 코멘트에 결과 게시
  -> plan 실패 시 check 실패
```

이 workflow가 `apply`를 하지 않는 이유:

- ECS, ALB, RDS, S3, IAM, Secrets, Route 53 같은 리소스는 영향 범위가 크다
- 그래서 변경 영향은 자동으로 보여주되, 실제 적용은 수동으로 통제한다

참고:

- 현재 Terraform 버전은 `1.10.0`
- `TF_VAR_db_password`는 GitHub Secret `TF_DB_PASSWORD`에서 주입한다

## 9. Backend 수동 롤백

파일: `.github/workflows/rollback-dev-backend.yml`

동작:

```text
workflow_dispatch
  -> rollback 대상 task definition 입력
  -> ECS service update
  -> services-stable 대기
  -> https://api.badasoft.com/health 200 확인
```

한계:

- DB migration은 되돌리지 못한다
- Secret 값 변경도 자동 복구하지 못한다
- Terraform 리소스 변경도 별도 복구가 필요하다

## 10. IAM Role 분리

| Role | 사용 Workflow | 권한 성격 |
| --- | --- | --- |
| `bada-dev-github-actions-deploy-role` | Backend CD, Worker CD, Backend rollback | ECR push, ECS 배포, Task Definition 등록, IAM PassRole |
| `bada-dev-github-actions-plan-role` | Terraform Plan-in-PR | Terraform plan 검토용 읽기 권한 중심 |

분리 이유:

- 배포 workflow는 쓰기 권한이 필요하다
- Terraform plan workflow는 읽기 권한 중심이면 충분하다
- 같은 Role을 쓰면 PR 실행 권한이 과도하게 커진다

## 11. 장애 시 확인 포인트

CI 실패:

- Ruff: 스타일/문법 경고 확인
- Bandit: medium/high 취약 패턴 확인
- pytest: Backend/Worker 테스트 실패 원인 확인
- eval: 샘플 데이터 회귀 결과 확인

Backend CD 실패:

- Docker build 실패
- ECR push 실패
- Task Definition 등록 실패
- ECS stable 대기 실패
- `/health` 200 실패

Worker CD 실패:

- Docker build 실패
- ECS stable 실패
- SQS 적체 증가
- DLQ 증가
- AccessDenied 로그

Mobile Build 실패:

- `EXPO_TOKEN` 누락 또는 인증 실패
- `npm ci` 실패
- EAS profile 설정 오류
- Expo 대시보드에 build가 생성되지 않음

Terraform Plan 실패:

- fmt 실패
- init 실패
- validate 실패
- plan 실패

## 12. 한 문장 요약

BADA의 CI/CD는 PR에서 코드와 Terraform 변경을 검증하고, develop merge 후 Backend와 Worker는 ECS Fargate에 자동 배포하며, 모바일 앱은 Expo EAS Build로 자동 제출하되, 실제 Terraform apply는 인프라 담당자가 수동으로 통제하는 구조다.
