# ─── WAF v2: Web ACL + OWASP Managed Rules + ALB 연결 ───────────────────────
#
# scope = REGIONAL (ALB 연결).
# CloudFront에 붙이려면 scope = CLOUDFRONT + us-east-1 provider 필요 — MVP 불필요.
#
# 규칙 우선순위:
#   1. AWSManagedRulesAmazonIpReputationList  — 알려진 악성 IP 차단
#   2. AWSManagedRulesCommonRuleSet           — OWASP Top 10 (SQLi, XSS 등)
#   3. AWSManagedRulesKnownBadInputsRuleSet   — Log4Shell, SSRF 등 공격 입력 차단
#
# 비용: Web ACL $5/월 + 규칙 $1/월 × 3 + 요청 $0.60/백만 건.
# 데모 트래픽 수준에서 추가 비용 미미.

resource "aws_wafv2_web_acl" "main" {
  name  = "${local.name_prefix}-web-acl"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  # 1. 악성 IP 평판 목록
  rule {
    name     = "AWSManagedRulesAmazonIpReputationList"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-ip-reputation"
      sampled_requests_enabled   = true
    }
  }

  # 2. OWASP 공통 규칙 (SQLi, XSS 등)
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-common-rules"
      sampled_requests_enabled   = true
    }
  }

  # 3. 알려진 악성 입력 (Log4Shell, SSRF 등)
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name_prefix}-web-acl"
    sampled_requests_enabled   = true
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-web-acl" })
}

# ALB에 Web ACL 연결
resource "aws_wafv2_web_acl_association" "alb" {
  resource_arn = aws_lb.main.arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}

# WAF 로그 → CloudWatch Log Group
resource "aws_cloudwatch_log_group" "waf" {
  # WAF 로그 그룹 이름은 반드시 "aws-waf-logs-" 로 시작해야 함 (AWS 제약)
  name              = "aws-waf-logs-${local.name_prefix}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-waf-logs" })
}

resource "aws_wafv2_web_acl_logging_configuration" "main" {
  log_destination_configs = [aws_cloudwatch_log_group.waf.arn]
  resource_arn            = aws_wafv2_web_acl.main.arn
}
