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

resource "aws_kms_key" "evidence" {
  description         = "${local.name_prefix} evidence encryption key"
  enable_key_rotation = true

  tags = local.common_tags
}

resource "aws_kms_alias" "evidence" {
  name          = "alias/${local.name_prefix}-evidence"
  target_key_id = aws_kms_key.evidence.key_id
}

resource "aws_s3_bucket" "evidence" {
  bucket = "${local.name_prefix}-evidence"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-evidence" })
}

resource "aws_s3_bucket" "report" {
  bucket = "${local.name_prefix}-report"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-report" })
}

resource "aws_s3_bucket_public_access_block" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "report" {
  bucket = aws_s3_bucket.report.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.evidence.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "report" {
  bucket = aws_s3_bucket.report.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.evidence.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_sqs_queue" "analysis_dlq" {
  name = "${local.name_prefix}-analysis-dlq"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-analysis-dlq" })
}

resource "aws_sqs_queue" "analysis" {
  name = "${local.name_prefix}-analysis"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.analysis_dlq.arn
    maxReceiveCount     = 5
  })

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-analysis" })
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-vpc" })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-igw" })
}

resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-public-${count.index + 1}"
    Tier = "public"
  })
}

resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-private-${count.index + 1}"
    Tier = "private"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-public-rt" })
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-private-rt" })
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-db-subnet-group" })
}

resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-alb-sg"
  description = "ALB security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-alb-sg" })
}

resource "aws_security_group" "ecs" {
  name        = "${local.name_prefix}-ecs-sg"
  description = "ECS security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "App traffic from ALB"
    from_port       = var.app_port
    to_port         = var.app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ecs-sg" })
}

resource "aws_security_group" "ssm_db_access" {
  name        = "${local.name_prefix}-ssm-db-access-sg"
  description = "SSM port forwarding access to private RDS"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "Outbound to VPC resources and AWS APIs"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ssm-db-access-sg" })
}

resource "aws_security_group" "rds" {
  name        = "${local.name_prefix}-rds-sg"
  description = "RDS security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Postgres from ECS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  ingress {
    description     = "Postgres from SSM DB access instance"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ssm_db_access.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-rds-sg" })
}

resource "aws_db_instance" "postgres" {
  identifier              = "${local.name_prefix}-postgres"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = var.db_instance_class
  allocated_storage       = var.db_allocated_storage
  db_name                 = "bada"
  username                = var.db_username
  password                = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  backup_retention_period = var.db_backup_retention_period
  deletion_protection     = var.db_deletion_protection
  skip_final_snapshot     = var.db_skip_final_snapshot
  final_snapshot_identifier = (
    var.db_skip_final_snapshot ? null : var.db_final_snapshot_identifier
  )
  apply_immediately   = var.db_apply_immediately
  publicly_accessible = false
  multi_az            = false

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-postgres" })
}

resource "aws_iam_role" "ssm_db_access" {
  name = "${local.name_prefix}-ssm-db-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ssm_db_access_core" {
  role       = aws_iam_role.ssm_db_access.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

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

resource "aws_cognito_user_pool" "main" {
  name = "${local.name_prefix}-user-pool"

  tags = local.common_tags
}

resource "aws_cognito_user_pool_client" "app" {
  name         = "${local.name_prefix}-app-client"
  user_pool_id = aws_cognito_user_pool.main.id
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

resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.name_prefix}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_task_execution_config_read" {
  name = "${local.name_prefix}-ecs-task-execution-config-read"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.app.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          aws_ssm_parameter.s3_evidence_bucket.arn,
          aws_ssm_parameter.s3_report_bucket.arn,
          aws_ssm_parameter.analysis_queue_url.arn,
          aws_ssm_parameter.aws_region.arn,
          aws_ssm_parameter.cognito_user_pool_id.arn,
          aws_ssm_parameter.cognito_client_id.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "ecs_task_app_access" {
  name = "${local.name_prefix}-ecs-task-app-access"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.evidence.arn,
          aws_s3_bucket.report.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.evidence.arn}/*",
          "${aws_s3_bucket.report.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.evidence.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl",
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = [
          aws_sqs_queue.analysis.arn,
          aws_sqs_queue.analysis_dlq.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "transcribe:StartTranscriptionJob",
          "transcribe:GetTranscriptionJob",
          "transcribe:DeleteTranscriptionJob",
          "transcribe:ListTranscriptionJobs",
          "translate:TranslateText"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.app.arn
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          aws_ssm_parameter.s3_evidence_bucket.arn,
          aws_ssm_parameter.s3_report_bucket.arn,
          aws_ssm_parameter.analysis_queue_url.arn,
          aws_ssm_parameter.aws_region.arn,
          aws_ssm_parameter.cognito_user_pool_id.arn,
          aws_ssm_parameter.cognito_client_id.arn
        ]
      }
    ]
  })
}

resource "aws_lb" "main" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-alb" })
}

resource "aws_lb_target_group" "backend" {
  name        = "${local.name_prefix}-tg"
  port        = var.app_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id

  health_check {
    enabled             = true
    path                = "/health"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 30
    timeout             = 5
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-tg" })
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/aws/ecs/${local.name_prefix}/backend"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-backend-logs" })
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/ecs/${local.name_prefix}/worker"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-worker-logs" })
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
        { name = "COGNITO_USER_POOL_ID", value = aws_cognito_user_pool.main.id },
        { name = "COGNITO_CLIENT_ID", value = aws_cognito_user_pool_client.app.id },
        { name = "RETENTION_DAYS", value = tostring(var.retention_days) }
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
        { name = "TRANSLATE_MODE", value = var.worker_translate_mode },
        { name = "STRUCTURED_ENGINE", value = var.worker_structured_engine },
        { name = "S3_BUCKET", value = aws_s3_bucket.evidence.bucket },
        { name = "SQS_QUEUE_URL", value = aws_sqs_queue.analysis.url }
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

resource "aws_ecs_service" "backend" {
  name            = "${local.name_prefix}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count
  launch_type     = "FARGATE"

  enable_execute_command = true

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

resource "aws_sns_topic" "alarms" {
  name = "${local.name_prefix}-alarm-notifications"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-alarm-notifications" })
}

resource "aws_sns_topic_subscription" "alarm_email" {
  for_each = toset(var.alarm_email_endpoints)

  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = each.value
}

resource "aws_cloudwatch_metric_alarm" "alb_target_5xx" {
  alarm_name          = "${local.name_prefix}-alb-target-5xx"
  alarm_description   = "Backend target 5xx responses from ALB are above the MVP threshold."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_action_arns
  ok_actions          = local.alarm_action_arns

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
    TargetGroup  = aws_lb_target_group.backend.arn_suffix
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-alb-target-5xx" })
}

resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_targets" {
  alarm_name          = "${local.name_prefix}-alb-unhealthy-targets"
  alarm_description   = "At least one backend target is unhealthy behind the ALB."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_action_arns
  ok_actions          = local.alarm_action_arns

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
    TargetGroup  = aws_lb_target_group.backend.arn_suffix
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-alb-unhealthy-targets" })
}

resource "aws_cloudwatch_metric_alarm" "backend_cpu_high" {
  alarm_name          = "${local.name_prefix}-backend-cpu-high"
  alarm_description   = "Backend ECS service CPU utilization is high."
  namespace           = "AWS/ECS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_action_arns
  ok_actions          = local.alarm_action_arns

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.backend.name
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-backend-cpu-high" })
}

resource "aws_cloudwatch_metric_alarm" "backend_memory_high" {
  alarm_name          = "${local.name_prefix}-backend-memory-high"
  alarm_description   = "Backend ECS service memory utilization is high."
  namespace           = "AWS/ECS"
  metric_name         = "MemoryUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_action_arns
  ok_actions          = local.alarm_action_arns

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.backend.name
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-backend-memory-high" })
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu_high" {
  alarm_name          = "${local.name_prefix}-rds-cpu-high"
  alarm_description   = "RDS PostgreSQL CPU utilization is high."
  namespace           = "AWS/RDS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_action_arns
  ok_actions          = local.alarm_action_arns

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres.identifier
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-rds-cpu-high" })
}

resource "aws_cloudwatch_metric_alarm" "rds_free_storage_low" {
  alarm_name          = "${local.name_prefix}-rds-free-storage-low"
  alarm_description   = "RDS PostgreSQL free storage is below 5 GiB."
  namespace           = "AWS/RDS"
  metric_name         = "FreeStorageSpace"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 1
  threshold           = 5368709120
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_action_arns
  ok_actions          = local.alarm_action_arns

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres.identifier
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-rds-free-storage-low" })
}

resource "aws_cloudwatch_metric_alarm" "sqs_analysis_backlog" {
  alarm_name          = "${local.name_prefix}-sqs-analysis-backlog"
  alarm_description   = "SQS analysis queue has visible messages waiting for processing."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 1
  threshold           = 10
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_action_arns
  ok_actions          = local.alarm_action_arns

  dimensions = {
    QueueName = aws_sqs_queue.analysis.name
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-sqs-analysis-backlog" })
}

resource "aws_cloudwatch_metric_alarm" "sqs_analysis_dlq_messages" {
  alarm_name          = "${local.name_prefix}-sqs-analysis-dlq-messages"
  alarm_description   = "SQS analysis dead-letter queue has at least one message."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_action_arns
  ok_actions          = local.alarm_action_arns

  dimensions = {
    QueueName = aws_sqs_queue.analysis_dlq.name
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-sqs-analysis-dlq-messages" })
}

resource "aws_secretsmanager_secret" "app" {
  name = "${local.name_prefix}/app-secrets"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-app-secrets" })
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    db_username  = var.db_username
    db_password  = var.db_password
    database_url = "postgresql+psycopg://${urlencode(var.db_username)}:${urlencode(var.db_password)}@${aws_db_instance.postgres.address}:5432/bada"
  })
}

resource "aws_ssm_parameter" "s3_evidence_bucket" {
  name  = "/${local.name_prefix}/s3/evidence_bucket"
  type  = "String"
  value = aws_s3_bucket.evidence.bucket

  tags = local.common_tags
}

resource "aws_ssm_parameter" "s3_report_bucket" {
  name  = "/${local.name_prefix}/s3/report_bucket"
  type  = "String"
  value = aws_s3_bucket.report.bucket

  tags = local.common_tags
}

resource "aws_ssm_parameter" "analysis_queue_url" {
  name  = "/${local.name_prefix}/sqs/analysis_queue_url"
  type  = "String"
  value = aws_sqs_queue.analysis.url

  tags = local.common_tags
}

resource "aws_ssm_parameter" "aws_region" {
  name  = "/${local.name_prefix}/config/aws_region"
  type  = "String"
  value = var.aws_region

  tags = local.common_tags
}

resource "aws_ssm_parameter" "cognito_user_pool_id" {
  name  = "/${local.name_prefix}/cognito/user_pool_id"
  type  = "String"
  value = aws_cognito_user_pool.main.id

  tags = local.common_tags
}

resource "aws_ssm_parameter" "cognito_client_id" {
  name  = "/${local.name_prefix}/cognito/client_id"
  type  = "String"
  value = aws_cognito_user_pool_client.app.id

  tags = local.common_tags
}

# Week 2 deployment foundation:
# - ECS task definitions and services are created with desired_count=0 by default.
# - GitHub Actions will build/push images first, then raise desired_count or update services.
# TODO (next stage):
# - PostGIS extension initialization strategy
# - Worker SQS consumer
