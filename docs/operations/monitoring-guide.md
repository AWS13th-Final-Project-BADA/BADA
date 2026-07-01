# 모니터링 팀원 인계

## 공유 메시지

모니터링 인프라 기본 구성을 완료했습니다.

- Prometheus/Grafana를 ECS Fargate에 배포했습니다.
- `https://monitor.badasoft.com` 접속과 Grafana health 200을 확인했습니다.
- Prometheus와 CloudWatch 데이터소스가 모두 정상 연결됐습니다.
- Prometheus 자체 및 Backend `/metrics` target이 모두 UP 상태입니다.
- BADA Overview 대시보드가 자동 생성되도록 구성했습니다.
- Grafana 비밀번호는 Secrets Manager `bada-dev/grafana-admin-password`에서 확인할 수 있습니다.
- Grafana ECS Task Role에는 `bada-dev-alarm-notifications` SNS Topic에만 메시지를 발행할 수 있는 `sns:Publish` 최소권한이 적용됐습니다.
- Grafana Alert `BADA-SNS` Contact Point, G1~G8 Rule 8개, 기본 Notification Policy receiver `BADA-SNS`를 provisioning으로 적용했습니다.

이제 모니터링 담당자는 다음 작업을 진행하면 됩니다.

1. Overview, Backend, Worker, Infrastructure 대시보드 패널을 실제 지표에 맞게 완성
2. ECS CPU·Memory, RDS, ALB 5xx, SQS 깊이 등 CloudWatch 패널 구성
3. Grafana Alert 이메일 실수신·OK 복구 검증
4. Worker exporter 구현 후 Prometheus target과 Worker 처리량 패널 추가
5. 음성 전사 E2E 실행 중 로그·지연·실패 지표를 대시보드에서 확인

### Worker Prometheus 메트릭 (2026-07-01 구현 완료)

Worker에 `prometheus_client` + `:9090/metrics` HTTP 서버가 추가됨. 계측 항목:
- `worker_sqs_messages_total{task_type, status}`: SQS 메시지 처리
- `worker_bedrock_calls_total{purpose, status}`: Bedrock 호출 횟수/레이턴시
- `worker_ocr_processed_total`: OCR 처리 건수
- `worker_stt_processed_total`: STT 전사 건수
- `worker_pdf_generated_total`: PDF 생성 건수
- `worker_analysis_duration_seconds`: 분석 전체 소요시간

**잔여 인프라 작업**: Prometheus scrape config에 Worker 타겟(`bada-dev-worker:9090`) 추가 필요.

완료 기준은 주요 대시보드가 실제 데이터를 표시하고, 테스트 장애나 임계치 초과 시 SNS 이메일과 OK 복구 알림이 정상 수신되는 것입니다.

## Grafana Alert 남은 작업

인프라 담당이 완료한 범위:

```text
Monitoring Task Role : bada-dev-monitoring-task-role
허용 작업            : sns:Publish
허용 대상            : bada-dev-alarm-notifications Topic 한정
Contact Point        : BADA-SNS
Alert Rules          : G1~G8 8개
Notification Policy  : receiver BADA-SNS
Terraform            : No changes
```

모니터링 담당이 진행할 범위:

1. Alert 이메일 수신과 정상화 후 OK 복구 알림 확인
2. 실제 운영 임계치가 과하거나 부족하면 G1~G8 Rule 튜닝 요청
3. Worker exporter 구현 후 G4/G5 Worker 처리량·지연 Rule이 실제 데이터를 보는지 확인
4. Grafana Editor 계정이 필요하면 인프라 담당에게 사용자명·이메일 전달

Dashboard JSON은 Alert 수신 검증의 필수 선행조건이 아니므로 이메일 수신 검증을 별도로 진행할 수 있습니다.

## 접속 정보

```text
Grafana URL : https://monitor.badasoft.com
Username    : admin
Secret      : bada-dev/grafana-admin-password
```

```bash
aws secretsmanager get-secret-value \
  --secret-id bada-dev/grafana-admin-password \
  --query SecretString \
  --output text
```
# Grafana Alert 테스트 시나리오

> terraform apply 후 `monitor.badasoft.com` 에서 검증.

---

## 사전 조건

1. Grafana ECS 새 Task revision 배포 완료
2. `monitor.badasoft.com/api/health` → 200
3. Grafana 로그인 (admin / Secrets Manager `bada-dev/grafana-admin-password`)

---

## 1. Contact Point 검증

**경로**: Alerting → Contact points

| 확인 항목 | 기대 결과 |
|-----------|-----------|
| `BADA-SNS` Contact Point 존재 | ✅ |
| Type = AWS SNS | ✅ |
| Topic ARN = `bada-dev-alarm-notifications` | ✅ |

**테스트 발송**:
1. `BADA-SNS` 우측 ⋮ → "Test"
2. `badajoa0710@gmail.com`에 테스트 이메일 도착 확인
3. 제목: `[BADA Alert] ...` 형식

---

## 2. Alert Rule 검증

**경로**: Alerting → Alert rules → BADA 폴더

| 그룹 | Rule | 상태 (트래픽 없을 때) |
|------|------|-----------------------|
| Service Health | G1 에러율 급증 | OK 또는 No Data (OK) |
| Service Health | G2 응답 지연 | OK 또는 No Data (OK) |
| Service Health | G3 트래픽 제로 | **Alerting** (정상 — 데모 환경은 트래픽 없음) |
| Worker | G4 Worker 실패율 | OK 또는 No Data (OK) |
| Worker | G5 Worker 처리 지연 | OK 또는 No Data (OK) |
| Database | G6 RDS 커넥션 포화 | OK |
| Business | G7 분석 실패 연속 | OK 또는 No Data (OK) |
| Business | G8 OCR 실패율 | OK 또는 No Data (OK) |

> **참고**: G3 "트래픽 제로"는 `noDataState: Alerting`이라 트래픽이 없으면 알림 발생함. 데모 환경에서는 이게 정상. 운영 시 트래픽이 있으면 OK로 전환됨.

---

## 3. 알림 발생 테스트 (수동)

### 방법 A: G3 트래픽 제로 (자연 발생)
- 10분간 `api.badasoft.com`에 요청 없으면 자동 Alerting
- SNS → 이메일 도착 확인

### 방법 B: G1 에러율 인위 발생
```bash
# 존재하지 않는 경로로 반복 요청 → 404 (5xx 아님, 이건 안 됨)
# 실제 5xx를 발생시키려면 백엔드에 버그를 주입해야 하므로 비추천
```

### 방법 C: Contact Point "Test" 버튼 (가장 안전)
1. Alerting → Contact points → BADA-SNS → Test
2. 이메일 도착 확인
3. 이것으로 SNS 연동 검증 충분

---

## 4. 알림 복구 테스트

### G3 복구 시나리오
1. 현재 Alerting 상태 확인 (트래픽 없어서 G3 firing)
2. `api.badasoft.com/health`에 요청 발생시킴:
   ```bash
   for i in $(seq 1 5); do curl -s https://api.badasoft.com/health; sleep 10; done
   ```
3. 10분 이내 G3 상태 → OK 전환
4. SNS로 "Resolved" 이메일 도착 확인

---

## 5. Dashboard 검증

**경로**: Dashboards → BADA 폴더

| 대시보드 | 패널 데이터 | 기대 |
|----------|------------|------|
| Overview | Prometheus 메트릭 | `/metrics` 엔드포인트 있으면 데이터 표시 |
| Infrastructure | CloudWatch | ECS CPU/Mem, RDS, ALB 데이터 즉시 표시 |
| Backend | Prometheus | `/metrics` 의존, 없으면 No data |
| Worker | Prometheus + CW | Worker 메트릭 없으면 Prometheus 패널 No data, SQS 패널은 표시 |

> **Infrastructure 대시보드는 즉시 데이터가 보여야 함** — CloudWatch는 AWS 자체 수집이라 추가 설정 불필요.

---

## 6. 체크리스트

- [ ] Grafana 로그인 성공
- [ ] Contact Point `BADA-SNS` 존재 확인
- [ ] Contact Point Test 이메일 수신
- [ ] Alert Rules BADA 폴더에 8개 규칙 존재
- [ ] Notification Policy 기본 수신자 = BADA-SNS
- [ ] Infrastructure 대시보드 CloudWatch 데이터 표시
- [ ] G3 Alerting → 요청 후 OK 전환 (복구 테스트)
- [ ] Resolved 이메일 수신
