# BADA 분산 k6 runner 인프라 (독립 Terraform, perf 전용)
# ⚠️ dev/prod state와 무관한 별도 state를 사용한다. perf ALB(public)를 인터넷으로 호출하므로
#    이 runner는 perf VPC의 public subnet에 public IP로 배치해 각 태스크가 고유 source IP로 egress한다.
#    (단일 NAT 뒤에 두면 source IP가 합쳐져 분산이 무의미 — README 참조)
#
# 관리 대상: ECR repo, CloudWatch Log Group, IAM(exec/task) role, Security Group, ECS Task Definition.
# 실제 RunTask 실행은 run-distributed.sh(스크립트)로 수행한다.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "bada"
      Environment = "perf"
      Component   = "k6-runner"
      ManagedBy   = "terraform"
    }
  }
}

locals {
  name = "bada-perf-k6-runner"
}

# ─── ECR ──────────────────────────────────────────────────────────────────
resource "aws_ecr_repository" "runner" {
  name                 = local.name
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  force_delete = true # 일회성 runner — destroy 시 이미지째 제거
}

# ─── CloudWatch Logs ────────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "runner" {
  name              = "/ecs/${local.name}"
  retention_in_days = 7
}

# ─── S3 결과 버킷 (source IP / k6 summary 업로드) ───────────────────────────
resource "aws_s3_bucket" "results" {
  bucket        = "${local.name}-results-${var.account_id}"
  force_destroy = true
}

# ─── IAM ────────────────────────────────────────────────────────────────────
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "exec" {
  name               = "${local.name}-exec-role"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}
resource "aws_iam_role_policy_attachment" "exec" {
  role       = aws_iam_role.exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name               = "${local.name}-task-role"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

# 최소 권한: 결과 버킷에 PutObject만 (Secrets/SSM 불필요)
resource "aws_iam_role_policy" "task_s3" {
  name = "${local.name}-s3-put"
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject"]
      Resource = "${aws_s3_bucket.results.arn}/*"
    }]
  })
}

# ─── Security Group: outbound only (perf ALB HTTP + checkip/ECR/S3/logs) ────
resource "aws_security_group" "runner" {
  name        = "${local.name}-sg"
  description = "k6 runner egress only"
  vpc_id      = var.vpc_id

  egress {
    description = "all outbound (perf ALB HTTP, checkip, ECR, S3, CloudWatch)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ─── ECS Task Definition ────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "runner" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.runner_cpu)
  memory                   = tostring(var.runner_memory)
  execution_role_arn       = aws_iam_role.exec.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([{
    name      = "k6-runner"
    image     = var.image_uri != "" ? var.image_uri : "${aws_ecr_repository.runner.repository_url}:latest"
    essential = true
    # TARGET_URL/VUS/DURATION/RUNNER_ID/SCENARIO/RESULT_S3_BUCKET는 RunTask overrides로 주입
    environment = [
      { name = "AWS_REGION", value = var.aws_region },
      { name = "RESULT_S3_BUCKET", value = aws_s3_bucket.results.bucket }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.runner.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "runner"
      }
    }
  }])
}
