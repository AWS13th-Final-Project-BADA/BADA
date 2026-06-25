# 고가용성 (High Availability) 설계

## 현재 상태: MVP 단일 인스턴스 구조

비용 최소화를 위해 의도적으로 단일 인스턴스로 운영 중이다.
단일 장애점(SPOF)이 존재하며, 프로덕션 전환 시 아래 계획을 적용한다.

### 현재 아키텍처의 SPOF

| 컴포넌트 | 현재 | SPOF 여부 | 장애 시 영향 |
|----------|------|-----------|-------------|
| Backend ECS | desired=1 | ⚠️ SPOF | API 전체 중단 |
| Worker ECS | desired=1 | ⚠️ SPOF | 비동기 분석 중단 (동기 분석은 유지) |
| Frontend ECS | desired=1 | ⚠️ SPOF | 웹 접속 불가 |
| RDS PostgreSQL | Single-AZ | ⚠️ SPOF | 전체 서비스 중단 |
| Prometheus | desired=1, 로컬 TSDB | ⚠️ SPOF | 메트릭 수집 중단 |
| Grafana | desired=1, EFS 영속화 | △ | 대시보드 접근 불가 (서비스 무영향) |
| ALB | AWS 관리형, Multi-AZ | ✅ HA | - |
| S3 | AWS 관리형, 11-9s 내구성 | ✅ HA | - |
| SQS | AWS 관리형, Multi-AZ | ✅ HA | - |
| Cognito | AWS 관리형 | ✅ HA | - |

### 현재도 갖춰진 요소

- 서브넷 2-AZ 분산 (ECS Task가 어느 AZ에든 배치 가능)
- ALB Multi-AZ 로드밸런싱
- ECS Circuit Breaker (배포 실패 자동 롤백)
- ECS 헬스체크 실패 시 Task 자동 교체
- SQS DLQ (메시지 처리 실패 격리)
- RDS 자동 백업 (기본 7일)

---

## 프로덕션 고가용성 계획

### Phase 1: 최소 HA (비용 +$30~50/월)

| 변경 | 내용 | 효과 |
|------|------|------|
| Backend desired=2 | 2개 Task, AZ 분산 | 1개 죽어도 서비스 유지 |
| RDS Multi-AZ | `multi_az = true` | 자동 장애조치 (30~60초 failover) |
| ECS Auto Scaling | CPU ≥ 70% → scale out | 트래픽 급증 대응 |

```hcl
# Backend Auto Scaling
resource "aws_appautoscaling_target" "backend" {
  max_capacity       = 4
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "backend_cpu" {
  name               = "backend-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend.resource_id
  scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = 70.0
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
```

```hcl
# RDS Multi-AZ
resource "aws_db_instance" "postgres" {
  # ... 기존 설정
  multi_az = true  # ← 이것만 변경
}
```

### Phase 2: 확장 HA (비용 +$80~120/월)

| 변경 | 내용 | 효과 |
|------|------|------|
| Worker Auto Scaling | SQS 메시지 수 기반 | 분석 요청 급증 대응 |
| RDS Read Replica | 읽기 전용 복제본 1개 | 조회 부하 분산 |
| ElastiCache Redis | 세션/캐시 | DB 부하 감소, 응답 속도 향상 |
| Cross-AZ ECS 배치 전략 | `spread(availability_zone)` | AZ 장애 시 자동 복구 |

```hcl
# Worker SQS 기반 Auto Scaling
resource "aws_appautoscaling_policy" "worker_sqs" {
  name               = "worker-sqs-scaling"
  policy_type        = "TargetTrackingScaling"
  # ...
  target_tracking_scaling_policy_configuration {
    target_value = 5.0  # Task당 메시지 5개 유지
    customized_metric_specification {
      metric_name = "ApproximateNumberOfMessagesVisible"
      namespace   = "AWS/SQS"
      statistic   = "Average"
      dimensions {
        name  = "QueueName"
        value = aws_sqs_queue.analysis.name
      }
    }
  }
}
```

### Phase 3: 재해 복구 (DR)

| 수준 | RTO | RPO | 방법 |
|------|-----|-----|------|
| Backup & Restore | 수 시간 | 24시간 | RDS 스냅샷 + S3 Cross-Region Replication |
| Pilot Light | 30분 | 5분 | 다른 리전에 인프라 코드만 준비, RDS 스냅샷 복원 |
| Warm Standby | 5분 | 1분 | 다른 리전에 축소 인프라 상시 운영 |

MVP에서는 Backup & Restore 수준이 현실적.

---

## 비용 비교

| 구성 | 월 비용 (추정) |
|------|---------------|
| 현재 (단일 인스턴스) | ~$80 |
| Phase 1 (최소 HA) | ~$120 |
| Phase 2 (확장 HA) | ~$200 |
| Phase 3 (DR 포함) | ~$350+ |

---

## 의사결정 근거

> MVP 단계에서는 비용 효율을 우선하되, 프로덕션 전환 시 최소 Phase 1을 적용한다.
> 고가용성 설계를 사전에 정의함으로써, 전환 시 Terraform 변수 몇 줄 변경으로 HA를 활성화할 수 있다.

**적용 기준**:
- 실 사용자 유입 시: Phase 1 즉시 적용
- MAU 1,000+ 시: Phase 2 적용
- SLA 계약 또는 규제 요건 시: Phase 3 검토
