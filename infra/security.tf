# ─── GuardDuty + Security Hub ───────────────────────────────────────────────
#
# GuardDuty: VPC 흐름 로그·DNS·CloudTrail 이벤트 분석 → 위협 탐지.
# Security Hub: GuardDuty·Config·Inspector 결과를 단일 대시보드로 집계.
#
# 비용: GuardDuty $4~$10/월 (데모 트래픽 수준), Security Hub $0.001/결과.
# 5주 MVP 예산(총 $1,500) 대비 미미.
#
# 종료(7/10): var.security_monitoring_enabled=false → detector/standards/
#   이벤트 규칙이 모두 제거되어 과금이 멈춘다. (콘솔 조작 없이 코드 한 줄)
#
# ⚠️ GuardDuty는 계정당 리전 단위로 한 번만 활성화 가능.
#    이미 콘솔에서 활성화되어 있으면 Terraform import 후 사용:
#    terraform import aws_guardduty_detector.main <detector-id>

resource "aws_guardduty_detector" "main" {
  count = var.security_monitoring_enabled ? 1 : 0

  enable = true

  datasources {
    s3_logs { enable = true }
    # kubernetes, malware_protection는 EKS 미사용 — 비활성
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-guardduty" })
}

# GuardDuty 고심각 위협 → SNS 알림
resource "aws_cloudwatch_event_rule" "guardduty_high" {
  count = var.security_monitoring_enabled ? 1 : 0

  name        = "${local.name_prefix}-guardduty-high-severity"
  description = "GuardDuty HIGH/CRITICAL 위협 탐지 시 알림"

  event_pattern = jsonencode({
    source      = ["aws.guardduty"]
    detail-type = ["GuardDuty Finding"]
    detail = {
      severity = [{ numeric = [">=", 7] }]
    }
  })

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-guardduty-high" })
}

resource "aws_cloudwatch_event_target" "guardduty_sns" {
  count = var.security_monitoring_enabled ? 1 : 0

  rule      = aws_cloudwatch_event_rule.guardduty_high[0].name
  target_id = "guardduty-high-sns"
  arn       = aws_sns_topic.alarms.arn
}

# ─── Security Hub ────────────────────────────────────────────────────────────

resource "aws_securityhub_account" "main" {
  count = var.security_monitoring_enabled ? 1 : 0
}

# AWS Foundational Security Best Practices — 가장 범용적인 표준
resource "aws_securityhub_standards_subscription" "fsbp" {
  count = var.security_monitoring_enabled ? 1 : 0

  depends_on    = [aws_securityhub_account.main]
  standards_arn = "arn:aws:securityhub:${var.aws_region}::standards/aws-foundational-security-best-practices/v/1.0.0"
}

# ─── State 주소 이전 (count 도입) ────────────────────────────────────────────
# 이미 배포된 무인덱스 리소스를 count 인덱스 0으로 이전한다. moved 블록이 없으면
# Terraform이 destroy 후 recreate로 계획해 GuardDuty/Security Hub가 재생성된다.
# security_monitoring_enabled=true(기본)에서는 주소만 바뀌고 리소스는 유지된다.
moved {
  from = aws_guardduty_detector.main
  to   = aws_guardduty_detector.main[0]
}

moved {
  from = aws_cloudwatch_event_rule.guardduty_high
  to   = aws_cloudwatch_event_rule.guardduty_high[0]
}

moved {
  from = aws_cloudwatch_event_target.guardduty_sns
  to   = aws_cloudwatch_event_target.guardduty_sns[0]
}

moved {
  from = aws_securityhub_account.main
  to   = aws_securityhub_account.main[0]
}

moved {
  from = aws_securityhub_standards_subscription.fsbp
  to   = aws_securityhub_standards_subscription.fsbp[0]
}
