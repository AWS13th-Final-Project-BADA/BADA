# 모니터링 팀원 인계

## 공유 메시지

모니터링 인프라 기본 구성을 완료했습니다.

- Prometheus/Grafana를 ECS Fargate에 배포했습니다.
- `https://monitor.badasoft.com` 접속과 Grafana health 200을 확인했습니다.
- Prometheus와 CloudWatch 데이터소스가 모두 정상 연결됐습니다.
- Prometheus 자체 및 Backend `/metrics` target이 모두 UP 상태입니다.
- BADA Overview 대시보드가 자동 생성되도록 구성했습니다.
- Grafana 비밀번호는 Secrets Manager `bada-dev/grafana-admin-password`에서 확인할 수 있습니다.

이제 모니터링 담당자는 다음 작업을 진행하면 됩니다.

1. Overview, Backend, Worker, Infrastructure 대시보드 패널을 실제 지표에 맞게 완성
2. ECS CPU·Memory, RDS, ALB 5xx, SQS 깊이 등 CloudWatch 패널 구성
3. Grafana Alert를 SNS 또는 이메일과 연결하고 테스트 알림 검증
4. Worker exporter 구현 후 Prometheus target과 Worker 처리량 패널 추가
5. 음성 전사 E2E 실행 중 로그·지연·실패 지표를 대시보드에서 확인

완료 기준은 주요 대시보드가 실제 데이터를 표시하고, 테스트 장애나 임계치 초과 시 알림이 정상 수신되는 것입니다.

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
