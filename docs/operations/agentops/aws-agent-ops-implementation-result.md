# AWS FinOps Agent · DevOps Agent 도입 및 검증 결과

최종 갱신: 2026-07-15

대상 계정: BADA AWS 교육 계정(외부 공유 문서에서는 계정 식별자 비공개)

대상 프로젝트: BADA — 취약근로자 증거 패키징 서비스

문서 목적: AWS Agent 기반 비용·장애 운영 자동화 도입 결과와 남은 검증 범위 기록

> 외부 공유와 포트폴리오용 요약은 [`aws-agent-ops-portfolio-report.md`](aws-agent-ops-portfolio-report.md)를 사용한다. 이 문서는 명령·실측·제약을 보존하는 상세 기술 기록이다.

---

## 1. 결론 요약

| 항목 | 결과 | 비고 |
| --- | --- | --- |
| AWS FinOps Agent | 실제 생성·검증 완료 | 버지니아 북부 리전에 Agent를 생성하고 Web App에서 비용·이상 징후·최적화 분석 실행 |
| Cost Anomaly Monitor | 생성 완료 | 서비스 단위 비용 이상 탐지 |
| Cost Anomaly SNS Subscription | 생성 완료 | 기존 BADA 운영 SNS Topic으로 비용 이상 즉시 알림 |
| Cost Budget Guardrail | 생성 완료 | 월 $1,500 한도와 실제 비용 50%·80%·100% 알림 |
| SNS 이메일 전달 | 검증 완료 | 수동 Publish부터 이메일 수신까지 확인 |
| AWS DevOps Agent | Agent Space 생성 완료 | 서울 미지원으로 도쿄 리전에 생성 |
| DevOps Agent Association | 생성 완료 | BADA 계정을 monitor account로 연결 |
| DevOps Agent Console 검증 | 완료 | Agent Space 유효, 토폴로지 관계 508개 매핑 확인 |
| Cost Optimization Hub 추천 | 확인 완료 | API 기준 조치 항목 7건, 월 예상 절감액 합계 $43.005 |
| Compute Optimizer ECS 추천 | 확인 완료 | 7월 15일 기준 ECS 추천 6건 생성 |
| 실제 RCA 실행 | 완료 | 과거 prod 배포 실패를 읽기 전용으로 조사하고 운영 기록·CloudTrail과 교차검증 |

이번 작업으로 BADA 계정에는 두 가지 운영 고도화 기반이 생겼다.

1. 비용 측면에서는 **AWS FinOps Agent를 실제 생성**하고 Cost Explorer, Cost Anomaly Detection, Cost Optimization Hub 데이터를 대상으로 자연어 분석을 실행했다.
2. 장애 운영 측면에서는 **도쿄 리전 DevOps Agent Agent Space**를 CloudFormation으로 생성하고, BADA 계정을 monitor association으로 연결했다.
3. 7월 15일 API 교차검증에서 7월 1~14일 추정 비용 $300.16, 비용 이상 9건·영향액 $42.45, 비용 최적화 조치 7건·월 예상 절감액 $43.005를 확인했다.
4. DevOps Agent Console은 BADA 계정의 리소스 관계 508개를 매핑했고, 실제 prod 장애 이력의 RCA를 수행했다.

추가로 2026년 7월 14일에는 과거 prod 초기 배포 실패를 대상으로 정식 Investigation을 실행했다. Agent는 CloudTrail, ECS service event와 task definition, Secrets Manager 상태를 교차 분석해 Secret version 생성 순서가 원인임을 식별했다. 다만 복구 배포의 정확한 실행 주체는 Agent 결과만으로 확정하지 못해, 운영 기록과 CloudTrail을 사람이 다시 확인하는 검증 게이트가 필요했다.

---

## 2. 공식 기능 기준 정리

### AWS FinOps Agent

AWS FinOps Agent는 비용 이상 징후를 조사하고, Cost Explorer, Cost Anomaly Detection, Cost Optimization Hub, Compute Optimizer, CloudTrail 등을 활용해 비용 증가 원인과 최적화 권고를 제공하는 Agent다.

BADA에서 의미 있는 활용 지점은 다음과 같다.

- Bedrock, Transcribe 같은 AI 기능 비용 증가 원인 분석
- ECS Fargate, RDS Multi-AZ, NAT Gateway 등 인프라 비용 증가 추적
- Cost Anomaly Detection 기반 비용 이상 징후 조사
- 비용 최적화 권고를 운영 태스크로 전환

### AWS DevOps Agent

AWS DevOps Agent는 Agent Space를 기반으로 AWS 계정, 로그, 메트릭, 배포 이력, 외부 도구를 연결해 release readiness와 incident root cause analysis를 지원하는 Agent다.

중요한 점은 **Agent Space가 생성된 리전과 실제 워크로드 리전이 반드시 같을 필요는 없다는 것**이다. AWS 공식 문서 기준으로, 지원 리전에 Agent Space를 만들면 연결된 AWS 계정의 여러 리전 리소스를 모니터링·조사할 수 있다. 따라서 BADA의 워크로드가 서울 리전에 있어도, DevOps Agent는 지원 리전인 도쿄에 Agent Space를 생성하는 방식으로 접근할 수 있다.

BADA에서 의미 있는 활용 지점은 다음과 같다.

- OAuth 503 같은 배포·설정 장애 원인 분석
- ALB 5XX, ECS task 재시작, SQS backlog 증가 분석
- CloudWatch Logs, Metrics, X-Ray, GitHub Actions 배포 이력 연결
- RCA 초안과 복구 절차 자동 생성

---

## 3. 실제 수행 내역

### 3.1 AWS 계정 확인

```bash
aws sts get-caller-identity
```

확인 결과는 로컬에서 검증했으며, 외부 공유 문서에는 계정 ID와 사용자 ARN을 기록하지 않는다.

```json
{
  "Account": "<redacted>",
  "Arn": "<redacted>"
}
```

기본 region:

```text
ap-northeast-2
```

---

### 3.2 FinOps Agent 선행 구성 — Cost Anomaly Monitor 생성

FinOps Agent 자체는 현재 로컬 AWS CLI의 독립 command로 제공되지 않았다.

```bash
aws finops-agent help
```

결과:

```text
invalid choice 'finops-agent'
```

따라서 FinOps Agent가 비용 이상 분석에 활용하는 선행 데이터 소스인 **AWS Cost Anomaly Detection**을 먼저 구성했다.

생성한 리소스:

```text
MonitorName : BADA-Service-Cost-Anomaly-Monitor
MonitorType : DIMENSIONAL
Dimension   : SERVICE
MonitorArn  : <redacted>
```

의미:

- 서비스 단위 비용 이상 징후를 탐지한다.
- Bedrock, ECS, RDS, ALB, WAF, NAT/VPC 등 BADA 비용 증가 원인을 서비스별로 분리해 볼 수 있다.
- 이후 실제 FinOps Agent를 활성화해 이 비용 이상 탐지 결과를 기반으로 원인 조사와 요약을 수행했다.

---

### 3.3 FinOps Agent 선행 구성 — Cost Anomaly SNS Subscription 생성

비용 이상 징후가 감지되면 기존 BADA 운영 알림 SNS Topic으로 즉시 알림이 가도록 구독을 생성했다.

생성한 리소스:

```text
SubscriptionName : BADA-FinOps-Agent-Cost-Anomaly-Subscription
SubscriptionArn  : <redacted>
Subscriber       : bada-dev-alarm-notifications
Frequency        : IMMEDIATE
Threshold        : $10 이상 비용 영향
Status           : CONFIRMED
```

의미:

- 비용 이상 징후가 $10 이상 영향을 줄 경우 즉시 SNS로 알림을 받을 수 있다.
- 기존 CloudWatch/SNS 운영 알림 체계에 비용 이상 탐지를 연결했다.
- 실제 Agent 활성화 전 비용 이상 탐지 운영 기반을 먼저 확보했고, 이후 Agent 분석 데이터 소스로 활용했다.

2026-07-15에는 해당 SNS Topic으로 테스트 메시지를 수동 발행해 구독 이메일에 도착하는 것을 확인했다. 이 검증은 `SNS Publish → 이메일 전달` 경로가 정상이라는 뜻이다. 실제 Cost Anomaly가 탐지되어 Subscription을 거쳐 이메일이 도착하는 전체 E2E는 다음 실발생 이벤트에서 별도로 확인한다. 원본 이메일 화면에는 계정 식별자와 수신 주소가 포함되어 공개 문서에는 첨부하지 않았다.

---

### 3.4 현재 비용 기준선 확인

2026-07-01부터 2026-07-14까지 Cost Explorer 기준 추정 비용은 $300.16이다. 결제 기간이 종료되지 않은 값이므로 최종 청구액과 다를 수 있다.

| 서비스 | 7월 1~14일 비용(USD) | 비중 |
| --- | ---: | ---: |
| EC2 - Other | 65.32 | 21.8% |
| Amazon Relational Database Service | 64.56 | 21.5% |
| Amazon Elastic Container Service | 42.88 | 14.3% |
| AmazonCloudWatch | 39.08 | 13.0% |
| Tax | 25.27 | 8.4% |
| Amazon Elastic Load Balancing | 19.42 | 6.5% |
| Amazon Virtual Private Cloud | 14.55 | 4.8% |
| AWS WAF | 12.18 | 4.1% |
| 전체 서비스 합계 | **300.16** | **100%** |

인사이트:

- 현재 비용 상위 항목은 RDS, EC2-Other, CloudWatch, ECS, ELB 순이다.
- BADA의 주요 운영 비용은 단순 AI 호출보다 인프라 상시 리소스에서 더 크게 발생하고 있다.
- FinOps Agent를 도입할 경우 우선 분석 대상은 Bedrock보다 RDS, ECS, CloudWatch, ALB, VPC/NAT 계층이 된다.
- AI 기능이 본격적으로 많이 사용되기 전까지는 Bedrock 비용보다 운영 인프라 고정비 관리가 더 중요하다.

---

### 3.5 Budget 상태 확인

2026-07-15 Console에서 `BADA-Project-Cost-Guardrail` Budget을 생성하고 정상 상태를 확인했다.

| 항목 | 설정값 |
| --- | --- |
| Budget 유형 | 월간 비용 예산 |
| 한도 | `$1,500` |
| 측정 기준 | 실제 비용(Actual cost) |
| 알림 임계값 | 50%(`$750`), 80%(`$1,200`), 100%(`$1,500`) |
| Budget Action | 없음 |

20:56 KST CLI 교차검증 결과 실제 비용은 `$307.421`(한도의 20.49%), 예측 비용은 `$652.421`(43.49%)이었으며 세 알림은 모두 `OK`였다. `DescribeBudgetActionsForBudget` 결과는 빈 목록으로, 자동 Action이 없다는 점도 확인했다.

Budget은 월간 총액 가드레일이고, Cost Anomaly Detection은 서비스별 비정상 비용 변화 탐지다. 두 기능을 함께 사용해 “총액 임계값 알림”과 “평소 패턴에서 벗어난 증가 알림”을 분리했다. 리소스 자동 중지 Action은 연결하지 않아 알림 이후 사람이 영향도와 롤백 가능성을 검토하도록 했다.

### 3.6 FinOps Agent 실제 생성 및 분석 검증

2026-07-15 버지니아 북부(`us-east-1`) 리전에 `BADA-FinOps-Agent`를 생성했다. Agent 역할과 Operator 역할은 Console wizard가 생성했으며 Jira·Slack 연동은 이번 검증 범위에서 제외했다. 분석은 읽기 전용으로 수행했고 리소스 중지·변경·구매는 실행하지 않았다.

#### 비용 분석

Web App에 7월 1~14일 비용과 상위 서비스를 질의했고, Cost Explorer API로 결과를 교차검증했다.

- Agent 응답: 추정 비용 $300.16
- API 응답: $300.1602133692, `Estimated=true`
- 상위 서비스와 금액은 양쪽이 일치했다.

#### 비용 이상 징후 분석

Agent는 같은 기간 비용 이상 9건과 영향액 합계 $42.45를 제시했고, Cost Anomaly Detection API 결과와 일치했다.

| 주요 이상 기간 | 영향액 | API에서 확인한 주요 원인 |
| --- | ---: | --- |
| 7월 10~13일 | $22.84 | NAT Gateway 처리량·시간과 리전 내 데이터 전송 증가 |
| 7월 14일 | $9.15 | RDS Multi-AZ `db.m6g.large` 사용 증가 |
| 7월 14일 | $8.97 | ECS Fargate ARM vCPU 사용 증가 |

AWS 응답은 첫 항목의 서비스 분류를 `Amazon Elastic Block Store`로 표시하면서 usage type은 NAT Gateway로 반환했다. 따라서 보고서에서는 서비스명만 보지 않고 root cause usage type까지 함께 해석했다.

#### 최적화 추천 분석

Agent는 월 예상 절감액 $43.01을 제시했고 합계는 API와 일치했다. 다만 Agent 화면은 “11개 추천”이라고 요약했지만 Cost Optimization Hub API에는 실제 조치 항목 7개가 존재했다. 이 문서에서는 **API의 7개를 기준값**으로 사용한다.

| 조치 | 항목 수 | 월 예상 절감액(USD) | 운영 판단 |
| --- | ---: | ---: | --- |
| RDS 중지 후보 | 2 | 30.46 | dev/prod 용도와 데모 일정을 확인하기 전 자동 적용 금지 |
| RDS Reserved Instance | 1 | 8.772 | 장기 운영 확정 후 구매 검토, 되돌릴 수 없어 즉시 적용 금지 |
| EC2 Graviton 전환 | 2 | 3.213 | 구현 난이도와 호환성 검증 필요 |
| RDS 스토리지 gp3 전환 | 2 | 0.56 | 변경 창과 성능 영향 검토 후 적용 |
| 합계 | **7** | **43.005** | 사람 승인 후 적용 |

Compute Optimizer API에서는 ECS 추천 6건을 확인했다. 그중 `bada-prod-prometheus`만 `Underprovisioned`, 성능 위험 `High`였으며 현재 256 CPU/512 MiB에서 512 CPU/1024 MiB로의 증설이 추천됐다. 이 항목은 FinOps Agent 답변에서 누락되어 API 교차검증으로 보완했다.

#### 실제 사용에서 확인한 제약

- Public preview의 콘텐츠 안전 필터가 복합 지시문 한 건을 차단했다. 비용·기간·질문 목적을 분리한 짧은 질의는 정상 처리됐다.
- Agent가 생성한 HTML 경영 요약 보고서를 로컬에 다운로드하고 SHA-256을 기록했다. 계정 ID·ARN·이메일·Access Key 패턴은 없었지만 내부 리소스명과 IP 형식 데이터가 포함되어 팀 공유 PR에서는 제외하고 개인 내부 증거로만 보관한다.
- Agent 응답은 분석 초안이며, 비용 수치·추천 건수·리소스 변경 여부는 공식 API와 사람이 최종 검증한다.

기계 판독 가능한 교차검증 요약은 [`evidence/finops-analysis-summary.json`](evidence/finops-analysis-summary.json)에 기록했다.

---

## 4. DevOps Agent 도입 및 리전 전환 결과

### 4.1 서울 리전 미지원 확인

처음에는 기존 BADA 워크로드가 있는 서울 리전(`ap-northeast-2`)에서 DevOps Agent를 생성하려 했다. 그러나 AWS Console에서 다음과 같이 표시되었다.

```text
Region Unsupported
AWS DevOps Agent is not available in Asia Pacific (Seoul).
```

지원 리전 목록에는 도쿄(`ap-northeast-1`)가 포함되어 있었다. DevOps Agent는 Agent Space가 생성된 지원 리전과 실제 워크로드 리전이 달라도 연결된 AWS 계정의 리소스를 조사할 수 있으므로, **Agent Space는 도쿄에 생성하고 BADA 서울 리소스를 교차 리전으로 조사하는 방식**으로 전환했다.

---

### 4.2 CloudFormation 리소스 지원 확인

도쿄 리전에서 DevOps Agent CloudFormation 리소스 타입이 제공되는지 확인했다.

```bash
aws cloudformation list-types \
  --region ap-northeast-1 \
  --visibility PUBLIC \
  --filters Category=AWS_TYPES \
  --query 'TypeSummaries[?starts_with(TypeName, `AWS::DevOpsAgent`)].TypeName' \
  --output text
```

확인 결과:

```text
AWS::DevOpsAgent::AgentSpace
AWS::DevOpsAgent::Association
AWS::DevOpsAgent::PrivateConnection
AWS::DevOpsAgent::Service
```

즉, 도쿄 리전에서는 CloudFormation으로 DevOps Agent Agent Space와 Association을 구성할 수 있었다.

---

### 4.3 CloudFormation 템플릿 작성

작성 파일:

```text
docs/operations/agentops/devops-agent-tokyo-agent-space.yaml
```

템플릿에 포함한 리소스:

| 리소스 | 역할 |
| --- | --- |
| `AWS::DevOpsAgent::AgentSpace` | BADA용 DevOps Agent Space |
| `AWS::DevOpsAgent::Association` | BADA AWS 계정을 monitor account로 연결 |
| `BADA-DevOpsAgentRole-AgentSpace` | DevOps Agent가 AWS 계정을 조사할 때 사용하는 IAM Role |
| `BADA-DevOpsAgentRole-WebappAdmin` | DevOps Agent Operator App 접근용 IAM Role |

템플릿 검증:

```bash
aws cloudformation validate-template \
  --template-body file://BADA-infra-workspace/docs/operations/agentops/devops-agent-tokyo-agent-space.yaml \
  --region ap-northeast-1
```

검증 결과:

```text
Parameters, Outputs, CAPABILITY_NAMED_IAM 확인 완료
```

---

### 4.4 Agent Space 배포

배포 명령:

```bash
aws cloudformation deploy \
  --template-file BADA-infra-workspace/docs/operations/agentops/devops-agent-tokyo-agent-space.yaml \
  --stack-name BADA-DevOpsAgent-Tokyo-AgentSpace \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-northeast-1 \
  --parameter-overrides \
    AgentSpaceName=BADA-DevOps-Agent-Space \
    AgentSpaceDescription='DevOps Agent Space for BADA operational investigation from Tokyo region'
```

배포 결과:

```text
Successfully created/updated stack - BADA-DevOpsAgent-Tokyo-AgentSpace
```

Stack 상태:

```text
CREATE_COMPLETE
```

Outputs:

| Output | 값 |
| --- | --- |
| AgentSpaceId | `<redacted>` |
| AgentSpaceArn | `<redacted>` |
| AgentSpaceRoleArn | `BADA-DevOpsAgentRole-AgentSpace` |
| OperatorRoleArn | `BADA-DevOpsAgentRole-WebappAdmin` |

---

### 4.5 생성 리소스 검증

```bash
aws cloudformation list-stack-resources \
  --stack-name BADA-DevOpsAgent-Tokyo-AgentSpace \
  --region ap-northeast-1
```

검증 결과:

| Logical ID | Type | Status |
| --- | --- | --- |
| AgentSpace | `AWS::DevOpsAgent::AgentSpace` | `CREATE_COMPLETE` |
| MonitorAssociation | `AWS::DevOpsAgent::Association` | `CREATE_COMPLETE` |
| DevOpsAgentSpaceRole | `AWS::IAM::Role` | `CREATE_COMPLETE` |
| DevOpsOperatorRole | `AWS::IAM::Role` | `CREATE_COMPLETE` |

Cloud Control API로 Agent Space 조회도 성공했다.

```bash
aws cloudcontrol get-resource \
  --type-name AWS::DevOpsAgent::AgentSpace \
  --identifier '<agent-space-id>' \
  --region ap-northeast-1
```

확인된 주요 속성:

```text
Name : BADA-DevOps-Agent-Space
Arn  : <redacted>
OperatorAppRoleArn : BADA-DevOpsAgentRole-WebappAdmin
```

---

### 4.6 실행 인터페이스와 한계

로컬 AWS CLI에서는 여전히 다음 명령이 제공되지 않았다.

```bash
aws devops-agent help
```

결과:

```text
invalid choice 'devops-agent'
```

따라서 Agent Space 생성과 기본 검증은 다음 경로로 수행했다.

- CloudFormation stack 상태
- CloudFormation resource 목록
- Cloud Control API resource 조회
- AWS Console의 DevOps Agent Agent Space 확인

실제 RCA는 AWS DevOps Agent의 공식 remote MCP endpoint를 SigV4로 호출해 수행했다. 로컬에 장기 Access Key를 추가하지 않고 현재 AWS 자격 증명으로 `mcp-proxy-for-aws`를 사용했으며, 조사 요청에는 읽기 전용 조건을 명시했다.

```text
Endpoint : https://connect.aidevops.ap-northeast-1.api.aws/mcp
Service  : aidevops
Region   : ap-northeast-1
```

DevOps Agent 전용 AWS CLI subcommand가 없다는 점은 Agent를 사용할 수 없다는 뜻이 아니다. Console Web App 또는 공식 remote MCP를 실행 인터페이스로 사용하면 된다.

---

### 4.7 DevOps Agent Console 검증

2026-07-10에 AWS Console에서 도쿄 리전의 Agent Space 화면을 직접 확인했다.

| 항목 | 확인 결과 |
| --- | --- |
| Agent Space | `BADA-DevOps-Agent-Space` |
| Region | `ap-northeast-1` |
| AgentSpaceId | `<redacted>` |
| Primary source 계정 | BADA AWS 교육 계정(식별자 비공개) |
| 계정 상태 | 유효 |
| 토폴로지 매핑 | 완료 |
| 매핑된 관계 | 508개 |
| 최종 업데이트 | 2026-07-10 13:06:50 KST |

의미:

- CloudFormation/API 관점뿐 아니라 Console UI에서도 Agent Space와 계정 association이 정상적으로 인식되는 것을 확인했다.
- DevOps Agent가 BADA 계정의 리소스 간 관계를 토폴로지로 매핑했으므로, 장애 조사에 사용할 운영 지식 기반은 형성된 상태다.
- 이 단계에서 리소스 매핑을 확인했고, 이후 4.8의 실제 Investigation으로 RCA 품질까지 검증했다.

---

### 4.8 실제 장애 RCA 실행 및 품질 검증

실서비스에 새 장애를 주입하지 않고, 2026년 7월 3일 prod 초기 배포에서 실제로 발생했던 장애 이력을 조사 대상으로 사용했다. 조사 범위는 `2026-07-03 07:07~07:54 UTC`이며 모든 요청은 읽기 전용으로 제한했다.

#### 실행 식별자

| 항목 | 값 |
| --- | --- |
| Agent Space | `BADA-DevOps-Agent-Space` |
| Agent Space ID | `<redacted>` |
| Task ID | `<redacted>` |
| Execution ID | `<redacted>` |
| Task type | `INVESTIGATION` |
| 실행 상태 | `COMPLETED` |
| 실행 시간 | 2026-07-14 06:50:31~06:54:44 UTC, 약 4분 13초 |

#### Agent가 식별한 사건 흐름

| 시각(UTC) | 확인 내용 |
| --- | --- |
| 07:07:53 | Terraform이 `bada-prod/app-secrets`의 shell만 생성. 값과 `AWSCURRENT`는 없음 |
| 07:09:18~07:15:19 | Worker task 약 7회 시작 실패 |
| 07:11:56~07:18:15 | Backend task 약 8회 시작 실패 |
| 07:15:43 / 07:17:46 | Worker / Backend 초기 deployment가 circuit breaker로 실패 |
| 07:34:44 | `PutSecretValue`로 첫 Secret version과 `AWSCURRENT` 생성 |
| 07:52:47 / 07:52:48 | 교차검증에서 Backend / Worker `force-new-deployment` 확인 |
| 07:53경 | 새 deployment task가 정상 기동 |
| 07:54:03 / 07:54:15 | Worker / Backend steady state 도달 |

Agent가 확정한 근본 원인은 **Terraform dependency 누락으로 ECS Service가 `aws_secretsmanager_secret_version`보다 먼저 기동된 것**이다. Task definition은 기본 stage인 `AWSCURRENT`를 참조했지만 약 27분 동안 해당 stage가 존재하지 않아 다음 오류로 초기화에 실패했다.

```text
ResourceInitializationError
ResourceNotFoundException: Secrets Manager can't find the specified secret value
for staging label: AWSCURRENT
```

이는 IAM `AccessDenied`가 아니라 존재하지 않는 Secret version stage를 조회한 오류였다. 컨테이너가 시작되기 전 실패했기 때문에 애플리케이션 로그가 없는 현상도 함께 설명된다.

#### 수동 근거와 교차검증

| 검증 항목 | Agent 결과 | 독립 검증 | 판정 |
| --- | --- | --- | --- |
| 근본 원인 | Secret shell과 version의 Terraform 순서 문제 | `CreateSecret` 요청에 `SecretString`/`SecretBinary`가 없고, task definition은 기본 `AWSCURRENT` stage를 참조함을 확인 | 일치 |
| Secret 공백 | 07:07:53~07:34:44, 약 27분 | CloudTrail `CreateSecret` 07:07:53, `PutSecretValue` 07:34:44 확인 | 일치 |
| 영향 서비스 | `bada-prod-backend`, `bada-prod-worker` | ECS 운영 기록과 일치 | 일치 |
| 오류 성격 | `ResourceNotFoundException`, IAM 오류 아님 | ECS service event와 일치 | 일치 |
| Circuit breaker | 두 서비스 모두 enable/rollback, 초기 배포라 되돌릴 안정 revision 없음 | 현재 ECS 설정과 운영 기록에서 `enable=true`, `rollback=true` 확인 | 일치 |
| 사건 구간 | 07:07~07:54 UTC, 약 47분 | 실제 task 실패·steady state 시각과 정합 | 일치 |
| 복구 트리거 | Agent는 증거 부족으로 확정 보류 | CloudTrail에서 07:52:47/48 `UpdateService(forceNewDeployment=true)` 확인 | 사람 검증으로 보완 |

#### RCA 품질 평가

- **강점**: 여러 AWS 데이터 소스를 약 4분 안에 교차 분석해 근본 원인, 영향 서비스, 오류 유형, circuit breaker 동작을 운영 기록과 일치하게 도출했다.
- **안전성**: 읽기 전용 지시를 준수했고 AWS 리소스를 변경하지 않았다.
- **한계**: 정식 Investigation은 복구 deployment의 새 ID와 성공 시각까지 찾았지만, 이를 시작한 `UpdateService` 이벤트는 놓쳐 정확한 복구 조치를 확정하지 못했다.
- **운영 판단**: DevOps Agent 결과는 RCA 초안과 탐색 범위 축소에 유용하지만, 복구·변경 이력은 CloudTrail과 운영 기록을 사람이 최종 확인해야 한다.

따라서 BADA의 권장 절차는 `Agent 조사 → 근거 링크·시각 확인 → CloudTrail/운영 기록 교차검증 → 복구 승인`이다. Agent가 제안한 내용을 자동 적용하는 구조로 사용하지 않는다.

---

## 5. BADA에 적용된 결과

### 실제 반영 완료

| 구분 | 반영 내용 |
| --- | --- |
| 비용 이상 탐지 | 서비스 차원 Cost Anomaly Monitor 생성 |
| 비용 알림 | 기존 BADA SNS Topic에 즉시 알림 구독 연결 |
| 비용 Budget | 월 $1,500 한도, 실제 비용 50%·80%·100% 알림 구성 |
| 비용 기준선 | 7월 1~14일 추정 비용 $300.16과 서비스별 상위 비용 분석 |
| FinOps Agent | 버지니아 북부 리전에 실제 생성하고 비용·이상 징후·최적화 질의 수행 |
| SNS 알림 경로 | 수동 SNS Publish부터 구독 이메일 수신까지 확인 |
| FinOps HTML 보고서 | Agent 생성 보고서를 저장하고 민감정보 패턴과 SHA-256 검증 |
| Compute Optimizer | 단일 계정 기준 활성화 완료 |
| Cost Optimization Hub | 단일 계정 기준 활성화 완료 |
| Cost Optimization Hub 추천 | API 기준 조치 항목 7건, 월 예상 절감액 $43.005 확인 |
| Compute Optimizer ECS 추천 | 7월 15일 기준 ECS 추천 6건 확인 |
| DevOps Agent Space | 도쿄 리전에 BADA DevOps Agent Space 생성 |
| DevOps Agent 계정 연결 | BADA AWS 계정을 monitor association으로 연결 |
| DevOps Agent Console 검증 | Agent Space 유효, Primary source 계정 연결, 토폴로지 관계 508개 확인 |
| DevOps Agent 실제 RCA | 과거 prod Secret version 생성 레이스를 정식 Investigation으로 분석하고 수동 증거와 교차검증 |
| IAM Role | Agent Space Role, Operator App Role 생성 |
| 관측 데이터 후보 | CloudWatch Logs, CloudWatch Alarm, X-Ray 서비스 그래프 확인 |
| 배포 이력 후보 | GitHub Actions Backend/Worker CD, Terraform Plan, Mobile Build workflow 확인 |
| 운영 문서 | Agent 기반 운영 고도화 전략과 도입 결과 문서화 |

### 후속 검증 필요

| 구분 | 남은 이유 |
| --- | --- |
| GitHub Actions 실제 연동 | workflow 존재는 확인했지만 DevOps Agent Web App 연결은 콘솔 작업 필요 |
| Grafana/Observability 실제 연동 | CloudWatch/X-Ray 데이터 존재는 확인했지만 Grafana 등 외부 도구 연결은 콘솔 작업 필요 |
| Jira/Slack 연동 | 외부 협업 도구 권한과 workspace 연결 필요 |
| 실제 비용 이상 알림 E2E | 수동 SNS→이메일 전달은 확인. 실제 Cost Anomaly 탐지 이벤트 발생→Subscription→이메일 수신은 관찰 필요 |

---

## 6. 운영·포트폴리오 관점 인사이트

### 6.1 FinOps 인사이트

- BADA의 현재 비용 리스크는 Bedrock보다 RDS, ECS, CloudWatch, ALB, VPC 같은 운영 인프라 계층이 더 크다.
- Budget은 월간 `$1,500` 총액과 50%·80%·100% 임계값을 통제하고, Cost Anomaly Detection은 서비스별 이상 징후를 조기에 탐지한다.
- 비용 이상 탐지를 기존 SNS 운영 알림 체계에 연결했기 때문에, 운영자는 비용 문제도 장애 알림과 비슷한 방식으로 인지할 수 있다.
- 수동 SNS 발행부터 이메일 수신까지 검증해 알림 운송 경로는 확인했지만, 실제 비용 이상 이벤트의 전체 E2E 여부는 별도로 구분해 기록했다.
- Compute Optimizer와 Cost Optimization Hub를 활성화해 향후 right-sizing과 비용 최적화 추천을 받을 수 있는 기반을 마련했다.
- 7월 15일 API 재조회 결과 Cost Optimization Hub에서 조치 항목 7건, Compute Optimizer ECS에서 추천 6건이 생성됐다.
- Agent가 추천 수를 11개로 요약한 반면 API 기준은 7개였다. 비용 합계는 일치했지만 건수는 공식 API를 기준으로 교정했다.
- Agent 답변에 없던 `bada-prod-prometheus`의 `Underprovisioned`·성능 위험 `High` 항목을 Compute Optimizer API 교차검증으로 보완했다.
- 추천 결과는 즉시 적용 대상이라기보다 운영자가 비용·성능 영향도를 검토할 후보 목록으로 활용해야 한다.

### 6.2 DevOps Agent 인사이트

- 서울 리전 미지원은 DevOps Agent 도입 자체의 블로커가 아니었다.
- 지원 리전인 도쿄에 Agent Space를 만들고, 연결된 AWS 계정 전체를 조사하게 하는 방식이 더 적절했다.
- BADA처럼 서울 리전에 운영 리소스가 있어도, Agent Space는 지원 리전에만 두고 운영 분석 계층으로 활용할 수 있다.
- Agent Space 생성과 실제 RCA 품질 검증은 다른 단계이므로 두 단계를 각각 수행했다.
- Console에서 Agent Space 유효 상태와 508개 리소스 관계 매핑을 확인해, DevOps Agent가 BADA 계정 토폴로지를 인식하고 있음을 검증했다.
- CloudWatch Logs, CloudWatch Alarm, X-Ray 서비스 그래프가 이미 존재하므로, DevOps Agent RCA에 연결할 관측 데이터 후보는 확보되어 있다.
- GitHub Actions에 Backend/Worker 배포, Terraform Plan, Mobile Build workflow가 존재하므로 배포 변경 이력과 장애 시점의 상관관계를 분석할 후보도 있다.
- 실제 prod 배포 실패 이력의 Investigation에서 Terraform Secret dependency 누락, `AWSCURRENT` 27분 공백, Backend/Worker circuit breaker 실패를 정확히 식별했다.
- 복구 실행 주체는 Agent가 확정하지 못했지만 CloudTrail을 사람이 재조회해 `force-new-deployment`를 확인했다. 이는 AgentOps에도 human-in-the-loop 검증 게이트가 필요하다는 실증 결과다.

---

## 7. 포트폴리오용 결과 정리

### 안전한 표현

> AWS FinOps Agent를 실제 생성해 7월 1~14일 비용 $300.16, 비용 이상 9건·영향액 $42.45, 최적화 조치 7건·월 예상 절감액 $43.005를 분석하고 공식 API와 교차검증했다. 장애 운영 측면에서는 서울 리전 미지원 문제를 도쿄 DevOps Agent Space로 우회하고 BADA 계정의 리소스 관계 508개를 매핑했다. 이후 실제 prod 배포 실패를 Investigation으로 분석해 Terraform Secret dependency 누락과 `AWSCURRENT` 생성 공백을 식별했으며, Agent가 확정하지 못한 복구 조치는 CloudTrail로 교차검증해 human-in-the-loop 운영 기준을 수립했다.

### 더 짧은 표현

> FinOps Agent의 비용·이상 징후·최적화 분석을 AWS API와 교차검증하고, 도쿄 DevOps Agent Space에서 실제 prod 장애 RCA를 실행했다. Agent 결과의 건수 차이와 누락 권고를 공식 API로 교정하고, 장애 복구 이력은 CloudTrail로 확인해 사람 승인 게이트를 포함한 AgentOps 절차를 설계했다.

### 피해야 할 표현

| 피해야 할 표현 | 이유 |
| --- | --- |
| “FinOps Agent가 비용을 자동 최적화했다.” | 실제 Agent 생성·분석은 완료했지만 리소스 변경과 구매는 수행하지 않음 |
| “DevOps Agent가 장애를 완전 자동 복구했다.” | 실제 RCA는 수행했지만 리소스 변경·복구는 하지 않았고 사람의 증거 검증이 필요 |
| “비용을 절감했다.” | 현재는 비용 이상 탐지 기반 구성과 기준선 분석 단계 |
| “서울 리전 DevOps Agent를 생성했다.” | 실제 Agent Space는 도쿄 리전에 생성 |
| “서비스를 도쿄 리전에 복제했다.” | 복제한 것은 워크로드가 아니라 운영 분석용 Agent Space |

---

## 8. 후속 작업 수행 결과

2026-07-10 이후 문서에 남아 있던 후속 작업 중 CLI/API 또는 Console로 확인 가능한 항목을 추가로 처리했다.

| 작업 | 수행 결과 | 증거/비고 |
| --- | --- | --- |
| Cost Anomaly Detection 알림 경로 테스트 | 전달 경로 완료 | 수동 SNS Publish 요청과 이메일 수신 확인. 실제 anomaly trigger E2E는 관찰 대기 |
| Cost Anomaly Subscription 상태 확인 | 확인 완료 | Subscription `CONFIRMED`, threshold `$10`, frequency `IMMEDIATE` |
| AWS Budget 생성 | 수행 완료 | 월 $1,500, Actual 50%·80%·100%, 세 알림 `OK`, Action 없음. 실제 $307.421·예측 $652.421 |
| FinOps HTML 비용 보고서 보관 | 수행 완료 | 7월 1~14일 Agent 보고서, SHA-256 및 민감정보 패턴 검사 완료 |
| Compute Optimizer 활성화 | 수행 완료 | `status=Active`, `memberAccountsEnrolled=false` |
| Cost Optimization Hub 활성화 | 수행 완료 | `status=Active`, 단일 계정 등록 완료 |
| FinOps Agent 실제 생성·질의 | 수행 완료 | 버지니아 북부 Agent 생성, 비용·이상 징후·최적화 분석 실행 |
| Cost Optimization Hub 추천 조회 | 확인 완료 | 2026-07-15 API 기준 조치 항목 7건, 월 예상 절감액 $43.005 |
| Compute Optimizer ECS 추천 조회 | 확인 완료 | 2026-07-15 기준 ECS 추천 6건 생성 |
| CloudWatch 관측 데이터 확인 | 확인 완료 | Metric Alarm 30개, dev/prod Backend·Worker·Grafana·Prometheus·X-Ray log group 확인 |
| X-Ray 서비스 그래프 확인 | 확인 완료 | 최근 조회 범위에서 `bada-backend` 서비스 확인 |
| GitHub Actions 배포 이력 후보 확인 | 확인 완료 | Backend/Worker CD, Terraform PR Plan, Mobile EAS Build workflow 존재 |
| DevOps Agent Console 확인 | 확인 완료 | Agent Space 유효, Primary source 계정 연결, 토폴로지 관계 508개 매핑 |
| DevOps Agent 실제 RCA | 수행 완료 | 조사 식별자는 비공개 처리, Terraform Secret dependency 레이스 식별 |
| RCA 독립 검증 | 수행 완료 | CloudTrail에서 `PutSecretValue`와 Backend/Worker `forceNewDeployment=true` 확인 |

### 8.1 2026-07-15 재검증 결과

활성화 직후에는 비용 최적화 추천이 0건이었지만, 며칠 뒤 재조회한 결과 실제 추천 데이터가 생성됐다.

#### Cost Optimization Hub 추천

| Action | 항목 수 | 예상 월 절감액(USD) | Implementation effort | 해석 |
| --- | ---: | ---: | --- | --- |
| Stop | 2 | 30.460 | Low | 유휴 또는 중지 후보 RDS의 실제 용도 확인 필요 |
| PurchaseReservedInstances | 1 | 8.772 | VeryLow | 장기 사용 확정 후 예약 인스턴스 검토 후보 |
| MigrateToGraviton | 2 | 3.213 | VeryHigh | Graviton 전환 후보이나 호환성 검증 필요 |
| Upgrade | 2 | 0.560 | Low | RDS 스토리지 gp3 전환 검토 후보 |
| 합계 | **7** | **43.005** | - | 자동 적용 없이 사람 승인 필요 |

해석:

- Cost Optimization Hub는 실제 비용 최적화 후보를 생성하기 시작했다.
- 절감액이 큰 항목은 `Stop`, `PurchaseReservedInstances`이지만, 운영 영향이 있거나 되돌릴 수 없으므로 자동 적용하지 않고 리소스 용도 확인이 먼저 필요하다.
- `MigrateToGraviton`은 예상 절감액은 작지만 구현 난이도가 높아, 포트폴리오에서는 “검토 후보”로만 다루는 것이 적절하다.
- Agent 화면의 11개 요약과 달리 API의 조치 항목은 7개였다. 이 표는 API를 기준으로 한다.

#### Compute Optimizer ECS 추천

| ECS Service | Finding | 현재 CPU/Memory | 권고 CPU/Memory | 성능 위험 |
| --- | --- | --- | --- | --- |
| `bada-dev-backend` | Optimized | 256 / 512 MiB | 256 / 512 MiB | - |
| `bada-dev-grafana` | Optimized | 256 / 512 MiB | 256 / 512 MiB | - |
| `bada-dev-prometheus` | Optimized | 256 / 512 MiB | 256 / 512 MiB | - |
| `bada-prod-backend` | Optimized | 256 / 512 MiB | 256 / 512 MiB | - |
| `bada-prod-grafana` | Optimized | 256 / 512 MiB | 256 / 512 MiB | - |
| `bada-prod-prometheus` | Underprovisioned | 256 / 512 MiB | 512 / 1024 MiB | High |

해석:

- 대부분의 ECS 서비스는 현재 사이징이 `Optimized`로 평가됐다.
- `bada-prod-prometheus`는 `Underprovisioned`로 확인되어 운영 모니터링 부하 증가 시 CPU/Memory 증설 후보로 볼 수 있다.
- 이 결과는 “무조건 비용 절감”이 아니라, 비용과 안정성을 함께 보는 FinOps 관점의 근거가 된다.

### 아직 수동으로 남은 항목

| 작업 | 남은 이유 | 다음 액션 |
| --- | --- | --- |
| GitHub Actions 실제 연동 | DevOps Agent Web App 또는 integration 설정 필요 | 배포 이력을 Agent RCA 입력으로 연결 |
| Grafana/외부 Observability 연동 | 외부 도구 연결 권한 필요 | CloudWatch/X-Ray 우선 사용, 필요 시 Grafana 연결 검토 |
| Slack/Jira 연동 | 외부 workspace 권한 필요 | 팀 협업 채널 결정 후 연결 |
| 실제 Cost Anomaly 알림 E2E | 인위적 비용 이상을 만들지 않고 실발생 이벤트를 기다려야 함 | 다음 anomaly 발생 시 탐지 시각·SNS·이메일 도착 시각 기록 |

---

## 9. 최종 평가

이번 작업은 Agent가 운영 변경을 자동 수행하게 만든 작업은 아니다. 비용 이상 탐지와 최적화 추천은 자동 수집하되, 장애 RCA는 Agent 조사 결과를 사람이 검증한 뒤 복구를 승인하는 형태로 구성했다.

핵심 성과는 다음과 같다.

1. Cost Anomaly Detection과 SNS 알림 경로를 구성하고 수동 발행부터 이메일 수신까지 확인해 비용 이상 알림의 전달 기반을 검증했다.
2. FinOps Agent를 실제 생성하고 비용·이상 징후·최적화 분석을 실행해 Cost Explorer·Cost Anomaly Detection·Cost Optimization Hub API와 교차검증했다.
3. Agent의 추천 건수 차이와 ECS 권고 누락을 API로 보정해, 생성형 분석 결과를 그대로 신뢰하지 않는 검증 절차를 수립했다.
4. BADA의 비용 기준선을 확인해 현재 비용 리스크가 AI 호출보다 운영 인프라 고정비에 더 크게 분포한다는 점을 정리했다.
5. 서울 리전 미지원으로 막힌 DevOps Agent를 지원 리전인 도쿄에 Agent Space로 생성해 우회했다.
6. CloudFormation으로 Agent Space, monitor association, IAM Role을 생성해 IaC 기반 AgentOps 도입 사례를 남겼다.
7. DevOps Agent Console에서 Agent Space 유효 상태와 508개 리소스 관계 매핑을 확인했다.
8. CloudWatch Logs, CloudWatch Alarm, X-Ray, GitHub Actions workflow를 확인해 DevOps Agent RCA에 연결할 관측·배포 데이터 후보를 식별했다.
9. 실제 prod 배포 실패를 정식 Investigation으로 분석해 Secret version 생성 레이스와 circuit breaker 실패를 운영 기록과 일치하게 식별했다.
10. Agent가 놓친 복구 트리거는 CloudTrail에서 수동 `force-new-deployment`로 확인해 Agent 결과에 사람의 증거 검증이 필요함을 실증했다.
11. 월 $1,500 Budget과 50%·80%·100% 알림을 추가해 이상 탐지와 별개의 총액 가드레일을 구성했다.
12. 포트폴리오에서는 “AWS Agent로 비용 이상 분석과 장애 RCA를 수행하고, 공식 API·CloudTrail 교차검증과 사람 승인 게이트를 포함한 AgentOps 운영 절차를 설계했다”라고 표현하는 것이 정확하다.
