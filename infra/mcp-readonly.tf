data "aws_iam_policy_document" "mcp_cloudwatch_assume_role" {
  statement {
    sid     = "AllowConfiguredOperators"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = var.mcp_operator_principal_arns
    }
  }
}

resource "aws_iam_role" "mcp_cloudwatch_readonly" {
  name               = "${var.project_name}-${var.environment}-mcp-cloudwatch-readonly-role"
  description        = "Read-only CloudWatch and CloudWatch Logs access for the local BADA MCP client"
  assume_role_policy = data.aws_iam_policy_document.mcp_cloudwatch_assume_role.json

  tags = {
    Name      = "${var.project_name}-${var.environment}-mcp-cloudwatch-readonly-role"
    ManagedBy = "Terraform"
    Purpose   = "MCP observability troubleshooting"
  }
}

data "aws_iam_policy_document" "mcp_cloudwatch_readonly" {
  statement {
    sid    = "ReadCloudWatchMetricsAndAlarms"
    effect = "Allow"
    actions = [
      "cloudwatch:DescribeAlarms",
      "cloudwatch:DescribeAlarmHistory",
      "cloudwatch:GetMetricData",
      "cloudwatch:ListMetrics",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ReadAndQueryCloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:DescribeLogGroups",
      "logs:DescribeQueryDefinitions",
      "logs:ListLogAnomalyDetectors",
      "logs:ListAnomalies",
      "logs:StartQuery",
      "logs:GetQueryResults",
      "logs:StopQuery",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "mcp_cloudwatch_readonly" {
  name   = "${var.project_name}-${var.environment}-mcp-cloudwatch-readonly-policy"
  role   = aws_iam_role.mcp_cloudwatch_readonly.id
  policy = data.aws_iam_policy_document.mcp_cloudwatch_readonly.json
}
