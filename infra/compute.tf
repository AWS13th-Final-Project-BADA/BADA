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

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = local.common_tags
}

# ─── Cluster Capacity Providers: FARGATE + FARGATE_SPOT (#15) ────────────────
# capacity_provider_strategy를 쓰는 서비스(Worker)는 클러스터에 해당 provider가
# 연결돼 있어야 한다. default 전략은 On-Demand FARGATE로 둬서, 전략/launch_type을
# 명시하지 않는 서비스는 기존대로 On-Demand로 배치된다(Backend는 launch_type 명시).
resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 0
  }
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
  task_role_arn            = aws_iam_role.ecs_task_backend.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.ecs_cpu_architecture
  }

  container_definitions = jsonencode(concat([
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
        { name = "RETENTION_DAYS", value = tostring(var.retention_days) },
        { name = "GPS_RETENTION_DAYS", value = tostring(var.gps_retention_days) },
        { name = "XRAY_ENABLED", value = tostring(var.backend_xray_enabled) },
        { name = "AWS_XRAY_DAEMON_ADDRESS", value = "127.0.0.1:2000" },
        { name = "AWS_XRAY_CONTEXT_MISSING", value = "LOG_ERROR" }
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
    ], var.backend_xray_enabled ? [
    {
      name              = "xray-daemon"
      image             = var.xray_daemon_image
      essential         = false
      cpu               = 32
      memoryReservation = 64
      command           = ["-o"]

      portMappings = [
        {
          containerPort = 2000
          hostPort      = 2000
          protocol      = "udp"
        }
      ]

      environment = [
        { name = "AWS_REGION", value = var.aws_region }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.xray[0].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "backend-xray"
        }
      }
    }
  ] : []))

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-backend-task" })
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name_prefix}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.worker_task_cpu)
  memory                   = tostring(var.worker_task_memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task_worker.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.ecs_cpu_architecture
  }

  container_definitions = jsonencode(concat([
    {
      name      = "worker"
      image     = local.worker_image
      essential = true

      portMappings = [
        {
          containerPort = 9090
          hostPort      = 9090
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "AWS_REGION", value = var.aws_region },
        { name = "PROVIDER_MODE", value = var.worker_provider_mode },
        { name = "TRANSCRIBE_MODE", value = var.worker_transcribe_mode != "" ? var.worker_transcribe_mode : var.worker_provider_mode },
        { name = "TRANSLATE_MODE", value = var.worker_translate_mode },
        { name = "STRUCTURED_ENGINE", value = var.worker_structured_engine },
        { name = "S3_BUCKET", value = aws_s3_bucket.evidence.bucket },
        { name = "S3_REPORT_BUCKET", value = aws_s3_bucket.report.bucket },
        { name = "DATABASE_SSL_MODE", value = "require" },
        { name = "SQS_QUEUE_URL", value = aws_sqs_queue.analysis.url },
        { name = "XRAY_ENABLED", value = tostring(var.worker_xray_enabled) },
        { name = "AWS_XRAY_DAEMON_ADDRESS", value = "127.0.0.1:2000" },
        { name = "AWS_XRAY_CONTEXT_MISSING", value = "LOG_ERROR" }
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
    ], var.worker_xray_enabled ? [
    {
      name              = "xray-daemon"
      image             = var.xray_daemon_image
      essential         = false
      cpu               = 32
      memoryReservation = 64
      command           = ["-o"]

      portMappings = [
        {
          containerPort = 2000
          hostPort      = 2000
          protocol      = "udp"
        }
      ]

      environment = [
        { name = "AWS_REGION", value = var.aws_region }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.xray[0].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "worker-xray"
        }
      }
    }
  ] : []))

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
    subnets          = local.ecs_service_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = local.ecs_assign_public_ip
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = var.app_port
  }

  health_check_grace_period_seconds = 60

  depends_on = [
    aws_lb_listener.http,
    aws_lb_listener.https,
    aws_lb_listener_rule.api,
    aws_secretsmanager_secret_version.app
  ]

  lifecycle {
    # desired_count: Application Auto Scaling(autoscaling.tf)이 관리하므로 무시.
    # 없으면 apply가 AS 조정값을 되돌려 스케일이 원복된다.
    ignore_changes = [task_definition, desired_count]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-backend-service" })
}

resource "aws_ecs_service" "worker" {
  name            = "${local.name_prefix}-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count

  # Spot 사용 시 launch_type 대신 capacity_provider_strategy 사용 (둘은 상호 배타).
  launch_type = var.worker_fargate_spot_enabled ? null : "FARGATE"

  # 기본: 순수 FARGATE_SPOT. worker_fargate_ondemand_base>0이면 그만큼 On-Demand로 고정.
  dynamic "capacity_provider_strategy" {
    for_each = var.worker_fargate_spot_enabled ? [1] : []
    content {
      capacity_provider = "FARGATE_SPOT"
      weight            = 1
      base              = 0
    }
  }

  dynamic "capacity_provider_strategy" {
    for_each = var.worker_fargate_spot_enabled && var.worker_fargate_ondemand_base > 0 ? [1] : []
    content {
      capacity_provider = "FARGATE"
      weight            = 0
      base              = var.worker_fargate_ondemand_base
    }
  }

  # capacity provider 전략 전환/변경은 새 배포로만 반영되므로 강제 재배포한다.
  force_new_deployment = var.worker_fargate_spot_enabled

  enable_execute_command = true

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = local.ecs_service_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = local.ecs_assign_public_ip
  }

  dynamic "service_registries" {
    for_each = var.monitoring_enabled ? [1] : []
    content {
      registry_arn = aws_service_discovery_service.worker[0].arn
    }
  }

  depends_on = [aws_secretsmanager_secret_version.app]

  lifecycle {
    # desired_count: Application Auto Scaling(autoscaling.tf)이 관리하므로 무시.
    # 없으면 apply가 AS 조정값을 되돌려 스케일이 원복된다.
    ignore_changes = [task_definition, desired_count]
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
    subnets          = local.ecs_service_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = local.ecs_assign_public_ip
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
