# ─── Compute: ECS / ECR / EC2(SSM) ─────────────────────────────────────────
resource "aws_iam_instance_profile" "ssm_db_access" {
  name = "${local.name_prefix}-ssm-db-access-profile"
  role = aws_iam_role.ssm_db_access.name

  tags = local.common_tags
}

resource "aws_instance" "ssm_db_access" {
  ami                         = data.aws_ami.amazon_linux_2023.id
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.public[0].id
  vpc_security_group_ids      = [aws_security_group.ssm_db_access.id]
  iam_instance_profile        = aws_iam_instance_profile.ssm_db_access.name
  associate_public_ip_address = true

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ssm-db-access"
    Role = "ssm-db-port-forwarding"
  })

  lifecycle {
    ignore_changes = [ami]
  }
}

resource "aws_ecr_repository" "backend" {
  name                 = "${local.name_prefix}-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-backend" })
}

resource "aws_ecr_repository" "worker" {
  name                 = "${local.name_prefix}-worker"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-worker" })
}

resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  tags = local.common_tags
}

resource "aws_ecr_repository" "frontend" {
  count = var.frontend_enabled ? 1 : 0
  name  = "${local.name_prefix}-frontend"

  image_scanning_configuration { scan_on_push = true }
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-frontend" })
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${local.name_prefix}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.backend_task_cpu)
  memory                   = tostring(var.backend_task_memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.ecs_cpu_architecture
  }

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = local.backend_image
      essential = true

      portMappings = [
        {
          containerPort = var.app_port
          hostPort      = var.app_port
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "AWS_REGION", value = var.aws_region },
        { name = "PROVIDER_MODE", value = var.backend_provider_mode },
        { name = "AUTH_MODE", value = var.backend_auth_mode },
        { name = "APP_BASE_URL", value = var.backend_app_base_url },
        { name = "GOOGLE_REDIRECT_URI", value = "https://api.badasoft.com/auth/google/callback" },
        { name = "KAKAO_REDIRECT_URI", value = "https://api.badasoft.com/auth/kakao/callback" },
        { name = "NAVER_REDIRECT_URI", value = "https://api.badasoft.com/auth/naver/callback" },
        { name = "CORS_ALLOWED_ORIGINS", value = join(",", var.backend_cors_allowed_origins) },
        { name = "AI_CHAT_MODE", value = var.backend_ai_chat_mode },
        { name = "EMBEDDING_MODE", value = var.backend_embedding_mode },
        { name = "DATABASE_AUTO_CREATE", value = tostring(var.database_auto_create) },
        { name = "DATABASE_SSL_MODE", value = "require" },
        { name = "DATABASE_POOL_SIZE", value = tostring(var.database_pool_size) },
        { name = "DATABASE_MAX_OVERFLOW", value = tostring(var.database_max_overflow) },
        { name = "STORAGE_MODE", value = "s3" },
        { name = "S3_BUCKET", value = aws_s3_bucket.evidence.bucket },
        { name = "KMS_KEY_ID", value = aws_kms_key.evidence.arn },
        { name = "SQS_QUEUE_URL", value = aws_sqs_queue.analysis.url },
        { name = "TRANSCRIPTION_DISPATCH_MODE", value = var.backend_transcription_dispatch_mode },
        { name = "TRANSCRIBE_MODE", value = var.backend_transcribe_mode != "" ? var.backend_transcribe_mode : var.backend_provider_mode },
        { name = "COGNITO_USER_POOL_ID", value = aws_cognito_user_pool.main.id },
        { name = "COGNITO_CLIENT_ID", value = aws_cognito_user_pool_client.app.id },
        { name = "COGNITO_DOMAIN", value = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com/" },
        { name = "COGNITO_REDIRECT_URI", value = var.cognito_callback_urls[0] },
        { name = "COGNITO_LOGOUT_URI", value = var.cognito_logout_urls[0] },
        { name = "COGNITO_SCOPES", value = join(" ", var.cognito_oauth_scopes) },
        { name = "RETENTION_DAYS", value = tostring(var.retention_days) }
      ]

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.app.arn}:database_url::"
        },
        { name = "GOOGLE_CLIENT_ID", valueFrom = "${aws_secretsmanager_secret.app.arn}:google_client_id::" },
        { name = "GOOGLE_CLIENT_SECRET", valueFrom = "${aws_secretsmanager_secret.app.arn}:google_client_secret::" },
        { name = "KAKAO_REST_API_KEY", valueFrom = "${aws_secretsmanager_secret.app.arn}:kakao_rest_api_key::" },
        { name = "KAKAO_CLIENT_SECRET", valueFrom = "${aws_secretsmanager_secret.app.arn}:kakao_client_secret::" },
        { name = "NAVER_CLIENT_ID", valueFrom = "${aws_secretsmanager_secret.app.arn}:naver_client_id::" },
        { name = "NAVER_CLIENT_SECRET", valueFrom = "${aws_secretsmanager_secret.app.arn}:naver_client_secret::" },
        { name = "JWT_SECRET", valueFrom = "${aws_secretsmanager_secret.app.arn}:jwt_secret::" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.backend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "backend"
        }
      }
    }
  ])

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-backend-task" })
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name_prefix}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.worker_task_cpu)
  memory                   = tostring(var.worker_task_memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.ecs_cpu_architecture
  }

  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = local.worker_image
      essential = true

      environment = [
        { name = "AWS_REGION", value = var.aws_region },
        { name = "PROVIDER_MODE", value = var.worker_provider_mode },
        { name = "TRANSCRIBE_MODE", value = var.worker_transcribe_mode != "" ? var.worker_transcribe_mode : var.worker_provider_mode },
        { name = "TRANSLATE_MODE", value = var.worker_translate_mode },
        { name = "STRUCTURED_ENGINE", value = var.worker_structured_engine },
        { name = "S3_BUCKET", value = aws_s3_bucket.evidence.bucket },
        { name = "S3_REPORT_BUCKET", value = aws_s3_bucket.report.bucket },
        { name = "DATABASE_SSL_MODE", value = "require" },
        { name = "SQS_QUEUE_URL", value = aws_sqs_queue.analysis.url }
      ]

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.app.arn}:database_url::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.worker.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "worker"
        }
      }
    }
  ])

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-worker-task" })
}

resource "aws_ecs_task_definition" "frontend" {
  count                    = var.frontend_enabled ? 1 : 0
  family                   = "${local.name_prefix}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.frontend_task_cpu)
  memory                   = tostring(var.frontend_task_memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.ecs_cpu_architecture
  }

  container_definitions = jsonencode([
    {
      name      = "frontend"
      image     = local.frontend_image
      essential = true

      portMappings = [
        {
          containerPort = 3000
          hostPort      = 3000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "HOSTNAME", value = "0.0.0.0" },
        { name = "PORT", value = "3000" },
        { name = "NEXT_PUBLIC_API_URL", value = "https://api.${var.domain_name}" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.frontend[0].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "frontend"
        }
      }
    }
  ])

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-frontend-task" })
}

resource "aws_ecs_service" "backend" {
  name            = "${local.name_prefix}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count
  launch_type     = "FARGATE"

  enable_execute_command = true

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = var.app_port
  }

  health_check_grace_period_seconds = 60

  depends_on = [aws_lb_listener.http]

  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-backend-service" })
}

resource "aws_ecs_service" "worker" {
  name            = "${local.name_prefix}-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  enable_execute_command = true

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-worker-service" })
}

resource "aws_ecs_service" "frontend" {
  count           = var.frontend_enabled ? 1 : 0
  name            = "${local.name_prefix}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend[0].arn
  desired_count   = var.frontend_desired_count
  launch_type     = "FARGATE"

  enable_execute_command = false

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend[0].arn
    container_name   = "frontend"
    container_port   = 3000
  }

  health_check_grace_period_seconds = 60

  depends_on = [aws_lb_listener_rule.frontend]

  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-frontend-service" })
}
