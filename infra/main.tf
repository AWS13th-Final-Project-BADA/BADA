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

  # ECS 서비스 네트워크 배치: ecs_in_private_subnets=true면 private subnet + public IP 제거.
  # (private 이전 전에 nat_gateway_enabled=true로 egress 경로가 있어야 한다)
  ecs_service_subnets  = var.ecs_in_private_subnets ? aws_subnet.private[*].id : aws_subnet.public[*].id
  ecs_assign_public_ip = var.ecs_in_private_subnets ? false : true

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
  # route53_zone_name이 있으면 그 존(부모 도메인)에 레코드를 만든다. 없으면 domain_name.
  name = var.route53_zone_name != "" ? var.route53_zone_name : var.domain_name
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
