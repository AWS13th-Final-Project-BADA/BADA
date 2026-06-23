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

이제 모니터링 담당자는 다음 작업을 진행하면 됩니다.

1. Overview, Backend, Worker, Infrastructure 대시보드 패널을 실제 지표에 맞게 완성
2. ECS CPU·Memory, RDS, ALB 5xx, SQS 깊이 등 CloudWatch 패널 구성
3. Grafana SNS Contact Point와 Alert Rule을 구성하고 이메일 수신·OK 복구 검증
4. Worker exporter 구현 후 Prometheus target과 Worker 처리량 패널 추가
5. 음성 전사 E2E 실행 중 로그·지연·실패 지표를 대시보드에서 확인

완료 기준은 주요 대시보드가 실제 데이터를 표시하고, 테스트 장애나 임계치 초과 시 알림이 정상 수신되는 것입니다.

## Grafana Alert 남은 작업

인프라 담당이 완료한 범위:

```text
Monitoring Task Role : bada-dev-monitoring-task-role
허용 작업            : sns:Publish
허용 대상            : bada-dev-alarm-notifications Topic 한정
Terraform            : No changes
```

모니터링 담당이 진행할 범위:

1. Grafana Contact Point를 Amazon SNS 방식으로 생성
2. Topic ARN에 `arn:aws:sns:ap-northeast-2:165749212250:bada-dev-alarm-notifications` 입력
3. Access Key와 Secret Key는 입력하지 않고 ECS Task Role 자격증명 사용
4. 임계치에 맞는 Alert Rule 연결
5. Alert 이메일 수신과 정상화 후 OK 복구 알림 확인

Dashboard JSON은 Alert 구성의 필수 선행조건이 아니므로 Contact Point·Alert Rule 검증을 별도로 진행할 수 있습니다.

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
