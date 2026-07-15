# ─── Auto Scaling: ECS Service (#4) ─────────────────────────────────────────
#
# Backend : 평균 CPU 기반 Target Tracking (사용자 대면 → 응답성이 부하 신호).
# Worker  : "태스크당 SQS 적체(backlog per task)" 기반 Target Tracking.
#           비동기 파이프라인(접수→SQS→Worker)에서는 CPU보다 큐 적체가
#           정확한 부하 신호다. AWS 권장 패턴:
#             backlog_per_task = ApproximateNumberOfMessagesVisible / RunningTaskCount
#           목표치(worker_backlog_target_per_task)를 넘으면 scale-out.
#
# ⚠️ 안전판(필수): backend/worker ECS 서비스의 lifecycle에
#    ignore_changes = [desired_count] 가 반드시 있어야 한다 (compute.tf 참조).
#    없으면 Auto Scaling이 조정한 desired_count를 다음 terraform apply가
#    되돌려 스케일이 원복되는 충돌이 발생한다.
#
# 비용: Application Auto Scaling 자체는 무료. Target Tracking이 자동 생성하는
#       CloudWatch alarm만 소액. 종료(7/10) 시 *_autoscaling_enabled=false로
#       target/policy 제거 후 desired_count를 고정하면 정리된다.
#
# 의존: Worker 지표는 ECS/ContainerInsights RunningTaskCount를 사용하므로
#       클러스터 Container Insights가 enabled여야 한다 (compute.tf에서 활성).

# ── Backend: CPU Target Tracking ────────────────────────────────────────────
resource "aws_appautoscaling_target" "backend" {
  count = var.backend_autoscaling_enabled ? 1 : 0

  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = var.backend_min_capacity
  max_capacity       = var.backend_max_capacity

  tags = local.common_tags
}

resource "aws_appautoscaling_policy" "backend_cpu" {
  count = var.backend_autoscaling_enabled ? 1 : 0

  name               = "${local.name_prefix}-backend-cpu-tt"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.backend[0].service_namespace
  resource_id        = aws_appautoscaling_target.backend[0].resource_id
  scalable_dimension = aws_appautoscaling_target.backend[0].scalable_dimension

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    target_value       = var.backend_cpu_target
    scale_out_cooldown = var.autoscaling_scale_out_cooldown
    scale_in_cooldown  = var.autoscaling_scale_in_cooldown
  }
}

# ── Worker: SQS backlog-per-task Target Tracking ─────────────────────────────
resource "aws_appautoscaling_target" "worker" {
  count = var.worker_autoscaling_enabled ? 1 : 0

  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.worker.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = var.worker_min_capacity
  max_capacity       = var.worker_max_capacity

  tags = local.common_tags
}

resource "aws_appautoscaling_policy" "worker_backlog" {
  count = var.worker_autoscaling_enabled ? 1 : 0

  name               = "${local.name_prefix}-worker-backlog-tt"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.worker[0].service_namespace
  resource_id        = aws_appautoscaling_target.worker[0].resource_id
  scalable_dimension = aws_appautoscaling_target.worker[0].scalable_dimension

  target_tracking_scaling_policy_configuration {
    target_value       = var.worker_backlog_target_per_task
    scale_out_cooldown = var.autoscaling_scale_out_cooldown
    scale_in_cooldown  = var.autoscaling_scale_in_cooldown

    # 태스크당 적체 = 대기 메시지 수 / 실행 중 Worker 태스크 수 (metric math)
    customized_metric_specification {
      metrics {
        id          = "backlog_per_task"
        label       = "Backlog messages per running worker task"
        expression  = "messages_visible / running_tasks"
        return_data = true
      }

      metrics {
        id          = "messages_visible"
        label       = "SQS ApproximateNumberOfMessagesVisible"
        return_data = false

        metric_stat {
          stat = "Average"

          metric {
            namespace   = "AWS/SQS"
            metric_name = "ApproximateNumberOfMessagesVisible"

            dimensions {
              name  = "QueueName"
              value = aws_sqs_queue.analysis.name
            }
          }
        }
      }

      metrics {
        id          = "running_tasks"
        label       = "ECS RunningTaskCount"
        return_data = false

        # min_capacity >= 1 이므로 0 나눗셈은 발생하지 않는다.
        metric_stat {
          stat = "Average"

          metric {
            namespace   = "ECS/ContainerInsights"
            metric_name = "RunningTaskCount"

            dimensions {
              name  = "ClusterName"
              value = aws_ecs_cluster.main.name
            }

            dimensions {
              name  = "ServiceName"
              value = aws_ecs_service.worker.name
            }
          }
        }
      }
    }
  }
}
