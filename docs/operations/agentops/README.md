# BADA AgentOps 문서 안내

최종 갱신: 2026-07-15
대상: BADA AWS 운영 고도화 — FinOps Agent·DevOps Agent

## 빠른 읽기 순서

1. 포트폴리오와 팀 공유가 목적이면 [`aws-agent-ops-portfolio-report.md`](aws-agent-ops-portfolio-report.md)를 먼저 읽는다.
2. 실제 명령, 구축 과정, 제약과 교차검증 근거가 필요하면 [`aws-agent-ops-implementation-result.md`](aws-agent-ops-implementation-result.md)를 읽는다.
3. 도쿄 DevOps Agent Space IaC는 [`devops-agent-tokyo-agent-space.yaml`](devops-agent-tokyo-agent-space.yaml)에서 확인한다.
4. 기계 판독 가능한 핵심 수치는 [`evidence/`](evidence/)의 JSON을 기준으로 한다.

## 문서별 역할

| 경로 | 역할 | 공유 범위 |
| --- | --- | --- |
| `aws-agent-ops-portfolio-report.md` | 문제·도입·정량 결과·운영 판단을 한눈에 보는 대표 보고서 | 팀·면접·포트폴리오 |
| `aws-agent-ops-implementation-result.md` | 구축과 검증 과정을 상세히 기록한 기술 보고서 | 팀·개인 학습 |
| `devops-agent-tokyo-agent-space.yaml` | Agent Space·Association·IAM Role CloudFormation 템플릿 | 팀·기술 검토 |
| `evidence/finops-analysis-summary.json` | 비용·이상 징후·최적화 API 교차검증 수치 | 검증·자동 처리 |
| `evidence/devops-agent-space-summary.json` | Agent Space와 토폴로지 매핑 상태 | 검증·자동 처리 |
| `evidence/devops-agent-rca-summary.json` | 장애 Investigation과 독립 검증 결과 | 검증·자동 처리 |
| `assets/*.png` | 검증 데이터를 발표·문서용으로 재구성한 시각 자료 | 팀·면접·포트폴리오 |

## 현재 검증 상태

| 영역 | 결과 |
| --- | --- |
| FinOps Agent | `us-east-1`에 실제 생성, 비용·이상 징후·최적화 질의 수행 |
| 비용 분석 | 2026-07-01~14 추정 비용 `$300.16`, Cost Explorer API와 일치 |
| 비용 이상 | 9건, 영향액 합계 `$42.45`, Cost Anomaly Detection API와 일치 |
| 비용 최적화 | API 기준 후보 `7건`, 월 예상 절감액 약 `$43.01` |
| 비용 가드레일 | 월 `$1,500` Budget 활성화, 실제 비용 기준 50%·80%·100% 알림 구성 |
| 알림 전달 | 수동 SNS Publish부터 이메일 수신까지 검증, 실제 Cost Anomaly 이벤트 E2E는 관찰 대기 |
| ECS 권고 | `bada-prod-prometheus` Underprovisioned·성능 위험 High 확인 |
| DevOps Agent | 서울 미지원으로 도쿄 Agent Space 구성, 관계 508개 매핑 |
| 실제 RCA | prod Secret version 생성 레이스를 식별하고 CloudTrail·운영 기록으로 검증 |

## 증거 사용 원칙

- Agent 응답보다 AWS 공식 API와 CloudTrail 결과를 기준값으로 사용한다.
- Agent가 권고한 리소스 중지·구매·변경을 자동 실행하지 않는다.
- 계정 ID, ARN, Agent Space ID, Task·Execution ID는 외부 공유 문서와 JSON에서 제외한다.
- `assets/` 이미지는 원본 콘솔 캡처가 아니라 검증된 수치를 재구성한 포트폴리오용 시각 자료다.
- Agent가 생성한 HTML 비용 보고서는 내부 리소스명과 IP 형식 데이터가 포함되어 공유 저장소에서 제외했다. 공식 수치는 JSON에 기록한 AWS API 결과를 우선한다.
- 이메일 수신 캡처처럼 계정 ID·이메일·구독 ARN이 포함된 원본 화면은 공개 폴더에 보관하지 않는다.
- 결제 기간이 끝나지 않은 Cost Explorer 값은 `Estimated=true`임을 함께 기록한다.
