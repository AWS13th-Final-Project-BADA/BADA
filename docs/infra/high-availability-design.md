# 고가용성 (High Availability) 설계

> 📌 **현황 업데이트 (2026-07-02)**: 아래 "Phase 1 최소 HA" 항목(Backend Auto Scaling·RDS Multi-AZ·Worker Auto Scaling)은 **이미 구현 완료**됐다(#4/#8, PR #203). 이 문서는 설계 근거·HCL 참조용으로 유지한다. 실제 적용 현황은 `docs/infra/implementation-status.md`, RTO/RPO 확정값과 복원 리허설은 `docs/operations/rto-rpo-and-restore-rehearsal.md`가 단일 출처다.

## 현재 상태: 최소 HA 적용 (Multi-AZ RDS + Auto Scaling)

MVP 단계에서 비용을 우선했으나, 2026-07-02 기준 아래 최소 HA가 적용됐다.
아래 SPOF 표는 현재(적용 후) 상태를 반영한다.

### 현재 아키텍처의 SPOF (2026-07-02 기준)

| 컴포넌트 | 현재 | SPOF 여부 | 장애 시 영향 |
|----------|------|-----------|-------------|
| Backend ECS | Auto Scaling min=1/max=3 (CPU 70%) | △ 완화 | 부하 시 scale-out, 상시 최소 1 |
| Worker ECS | Auto Scaling min=1/max=3 (SQS backlog) | △ 완화 | 적체 시 scale-out |
| RDS PostgreSQL | **Multi-AZ (encrypted)** | ✅ HA | 자동 failover 30~60초 |
| Prometheus | desired=1, 로컬 TSDB | ⚠️ SPOF | 메트릭 수집 중단 (서비스 무영향) |
| Grafana | desired=1, EFS 영속화 | △ | 대시보드 접근 불가 (서비스 무영향) |
| ALB | AWS 관리형, Multi-AZ | ✅ HA | - |
| S3 | AWS 관리형, 11-9s 내구성 | ✅ HA | - |
| SQS | AWS 관리형, Multi-AZ | ✅ HA | - |

> Frontend ECS는 제거됨(`frontend_enabled=false`, 모바일 앱 전환). `badasoft.com`은 Backend 폴백.
> 남은 SPOF는 Prometheus/Grafana(관측 계층)로, 서비스 트래픽에는 영향 없다.

### 현재도 갖춰진 요소

- 서브넷 2-AZ 분산 (ECS Task가 어느 AZ에든 배치 가능)
- ALB Multi-AZ 로드밸런싱
- ECS Circuit Breaker (배포 실패 자동 롤백)
- ECS 헬스체크 실패 시 Task 자동 교체
- SQS DLQ (메시지 처리 실패 격리)
- RDS 자동 백업 (기본 7일)

---

## 프로덕션 고가용성 계획

### Phase 1: 최소 HA (비용 +$30~50/월) — ✅ 적용 완료 (2026-07-02)

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

> DR 수준(Backup&Restore / Pilot Light / Warm Standby)과 확정 RTO/RPO, 복원 리허설
> 절차·워크시트는 **단일 출처** `docs/operations/rto-rpo-and-restore-rehearsal.md`를 참조한다.
> MVP에서는 Backup & Restore 수준이 현실적(RDS 자동 백업 7일 활성).

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
