# BADA 인프라 개요

## 문서 목적

이 문서는 BADA 서비스의 AWS 인프라 구조와 운영 기준을 팀 공용 관점에서 설명하기 위한 문서다.

목표는 아래와 같다.

- 현재 BADA가 어떤 인프라 구조를 기준으로 설계되었는지 빠르게 이해할 수 있게 한다.
- 왜 이 서비스를 이런 AWS 스택으로 구성했는지 설명한다.
- 현재 Terraform으로 어디까지 반영되었고, 무엇이 다음 단계인지 구분한다.

---

## 1. 인프라 한 줄 요약

> BADA는 `ALB + ECS Fargate + RDS PostgreSQL + PostGIS + S3 + KMS + SQS + DLQ + Cognito + Secrets Manager + SSM + CloudWatch + Terraform` 구조를 기준으로 설계된 AWS 관리형 서비스 중심 아키텍처를 사용한다.

---

## 2. 왜 이런 인프라가 필요한가

BADA는 외국인 근로자가 계약서, 급여명세서, 대화 캡처, 통장내역, 음성 파일 같은 증거를 업로드하면,  
이를 구조화하고 상담/신고 준비용 결과물로 정리하는 서비스다.

이 흐름을 인프라 관점으로 보면 아래 기능이 필요하다.

- 외부 요청을 받는 API 진입점
- backend와 worker를 분리할 실행 환경
- 원본 증거와 산출물을 저장할 파일 스토리지
- OCR / LLM / 번역 작업을 비동기로 처리할 큐
- 사건 정보와 분석 결과를 저장할 관계형 DB
- 사용자 인증
- 시크릿과 일반 설정의 분리 관리
- 운영 로그와 기본 모니터링

---

## 3. 인프라 구성 요소

| 서비스 | 역할 | 선택 이유 |
| --- | --- | --- |
| `Terraform` | AWS 인프라를 코드로 관리 | 재현성, 변경 이력 관리, 협업 용이성 |
| `ALB` | 외부 요청 진입점 | ECS backend와 자연스럽게 연결 가능 |
| `ECS Fargate` | backend / worker 실행 | 서버 관리 없이 컨테이너 운영 가능 |
| `ECR` | 컨테이너 이미지 저장 | backend / worker 이미지 배포용 |
| `RDS PostgreSQL` | 사건/사용자/분석 결과 저장 | 관계형 데이터 구조에 적합 |
| `PostGIS` | 위치 데이터 계산 | GPS 저장 및 지오펜스 처리 |
| `S3` | 원본 증거 / 산출물 저장 | 객체 스토리지로 파일 관리에 적합 |
| `KMS` | 암호화 키 관리 | 민감한 증거 파일 보호 |
| `SQS` | 분석 작업 큐 | backend와 worker를 비동기 구조로 분리 |
| `DLQ` | 실패 작업 보관 | 분석 실패 작업 추적 및 재처리 판단 |
| `Cognito` | 사용자 인증 | 관리형 인증 구조 사용 |
| `Secrets Manager` | 민감한 값 저장 | DB 비밀번호, API 키 보관 |
| `SSM Parameter Store` | 비민감 설정 저장 | bucket, queue url, region 등 관리 |
| `CloudWatch Logs` | 로그 수집 | backend / worker 로그 확인 |
| `CloudWatch Alarms` | 모니터링 확장 기준 | 이후 CPU, 메모리, 큐 적체 알림 가능 |

---

## 4. 네트워크 원칙

BADA 인프라는 아래 네트워크 기준을 따른다.

- `ALB / ECS`: public subnet
- `RDS`: private subnet
- `NAT Gateway`: 사용하지 않음

### 이유

- 앱과 외부 사용자의 요청은 ALB를 통해 backend로 들어와야 한다.
- 데이터베이스는 외부에 직접 노출하지 않고 backend에서만 접근하도록 제한해야 한다.
- 프로젝트 운영 기간이 짧고 총 예산이 제한되어 있어 NAT Gateway의 고정비는 제외한다.

---

## 5. 비용 운영 기준

- 프로젝트 운영 기간: `2026-06-04 ~ 2026-07-10`
- 팀 전체 AWS 총 예산: `1,500달러`

### 비용 통제 원칙

- `NAT Gateway` 미사용
- `RDS Single-AZ`
- `Fargate` 최소 안정 사양부터 시작
- `CloudWatch Logs` 보존기간은 짧게 운영
- 민감정보는 `Secrets Manager`, 비민감 설정은 `SSM`으로 분리

즉, BADA 인프라는 **AI(Bedrock / OCR / 번역) 비용을 함께 고려하면서도 데모 안정성을 해치지 않는 수준**을 목표로 한다.

---

## 6. 현재 Terraform 반영 범위

현재 `infra/` 디렉토리의 Terraform 코드에는 아래 리소스가 반영되어 있다.

### 반영 완료

- VPC
- public subnet / private subnet
- Internet Gateway
- route table / association
- S3 evidence bucket
- S3 report bucket
- KMS key / alias
- SQS queue / DLQ
- RDS / DB subnet group / security group
- ECS cluster
- ALB / listener / target group
- ECR backend / worker repository
- Cognito user pool / app client
- Secrets Manager secret
- SSM Parameter Store
- CloudWatch log groups

### 다음 단계

- ECS task definition
- ECS service
- ALB target과 ECS 실제 연결
- Secrets / SSM 런타임 주입
- CloudWatch alarms 세부화
- GitHub Actions 기반 배포 자동화

---

## 7. 현재 구현 상태를 어떻게 이해하면 되는가

현재 상태는 “문서만 있는 설계”가 아니라,  
**Terraform 기준으로 핵심 인프라 리소스 골격이 실제 코드에 반영된 상태**다.

즉:

- 인프라 구조는 확정되었고
- 코드로도 옮겨졌으며
- 이후 단계는 애플리케이션 배포와 운영 연결을 붙이는 작업이다

---

## 8. 관련 파일

- `infra/providers.tf`
- `infra/variables.tf`
- `infra/main.tf`
- `infra/outputs.tf`
- `infra/README.md`
- `docs/aws-setup-checklist.md`

---

## 9. 한 줄 정리

> BADA 인프라는 AWS 관리형 서비스 중심으로 설계되었으며, 현재는 Terraform 기준의 핵심 인프라 골격이 준비된 상태이고, 다음 단계는 ECS 서비스와 배포 자동화를 실제 서비스 흐름에 연결하는 것이다.
