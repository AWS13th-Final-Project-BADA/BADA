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
