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
