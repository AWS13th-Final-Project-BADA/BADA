# ─── GuardDuty + Security Hub ───────────────────────────────────────────────
#
# GuardDuty: VPC 흐름 로그·DNS·CloudTrail 이벤트 분석 → 위협 탐지.
# Security Hub: GuardDuty·Config·Inspector 결과를 단일 대시보드로 집계.
#
# 비용: GuardDuty $4~$10/월 (데모 트래픽 수준), Security Hub $0.001/결과.
# 5주 MVP 예산(총 $1,500) 대비 미미.
#
# ⚠️ GuardDuty는 계정당 리전 단위로 한 번만 활성화 가능.
#    이미 콘솔에서 활성화되어 있으면 Terraform import 후 사용:
#    terraform import aws_guardduty_detector.main <detector-id>

resource "aws_guardduty_detector" "main" {
  enable = true

  datasources {
    s3_logs { enable = true }
    # kubernetes, malware_protection는 EKS 미사용 — 비활성
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-guardduty" })
}

# GuardDuty 고심각 위협 → SNS 알림
resource "aws_cloudwatch_event_rule" "guardduty_high" {
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
  rule      = aws_cloudwatch_event_rule.guardduty_high.name
  target_id = "guardduty-high-sns"
  arn       = aws_sns_topic.alarms.arn
}

# ─── Security Hub ────────────────────────────────────────────────────────────

resource "aws_securityhub_account" "main" {}

# AWS Foundational Security Best Practices — 가장 범용적인 표준
resource "aws_securityhub_standards_subscription" "fsbp" {
  depends_on    = [aws_securityhub_account.main]
  standards_arn = "arn:aws:securityhub:${var.aws_region}::standards/aws-foundational-security-best-practices/v/1.0.0"
}
