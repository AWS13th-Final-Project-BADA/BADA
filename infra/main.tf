locals {
  name_prefix = "${var.project_name}-${var.environment}"
  backend_image = (
    var.api_container_image != "replace-me"
    ? var.api_container_image
    : "${aws_ecr_repository.backend.repository_url}:latest"
  )
  worker_image = (
    var.worker_container_image != "replace-me"
    ? var.worker_container_image
    : "${aws_ecr_repository.worker.repository_url}:latest"
  )
  frontend_image = (
    var.frontend_container_image != "replace-me"
    ? var.frontend_container_image
    : try("${aws_ecr_repository.frontend[0].repository_url}:latest", "frontend-disabled")
  )
  alarm_action_arns = concat(
    var.alarm_actions,
    length(var.alarm_email_endpoints) > 0 ? [aws_sns_topic.alarms.arn] : []
  )

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}












































# ─── HTTPS / ACM / Route 53 / Host Routing ───────────────────────────────────

data "aws_route53_zone" "main" {
  count = var.domain_name != "" ? 1 : 0
  name  = var.domain_name
}







# Route 53 DNS records → ALB



# ─── Frontend ECR + Target Group ─────────────────────────────────────────────



# ─── ALB Access Logging ──────────────────────────────────────────────────────









































# Week 2 deployment foundation:
# - ECS task definitions and services are created with desired_count=0 by default.
# - GitHub Actions will build/push images first, then raise desired_count or update services.
# TODO (next stage):
# - PostGIS extension initialization strategy
# - Worker SQS consumer
