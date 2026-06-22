# ─── 모니터링 인프라: Prometheus + Grafana (ECS Fargate) ────────────────────

locals {
  monitoring_service_discovery_namespace = "${local.name_prefix}.local"
  prometheus_config_base64 = base64encode(templatefile(
    "${path.module}/../monitoring/prometheus/prometheus.yml",
    { domain_name = var.domain_name }
  ))
  grafana_datasources_base64 = base64encode(templatefile(
    "${path.module}/../monitoring/grafana/provisioning/datasources/datasources.yml",
    {
      aws_region                  = var.aws_region
      service_discovery_namespace = local.monitoring_service_discovery_namespace
    }
  ))
  grafana_dashboards_config_base64 = filebase64(
    "${path.module}/../monitoring/grafana/provisioning/dashboards/dashboards.yml"
  )
  grafana_overview_dashboard_base64 = filebase64(
    "${path.module}/../monitoring/grafana/provisioning/dashboards/json/bada-overview.json"
  )
}

# Prometheus는 외부에 노출하지 않고 Grafana가 VPC 내부 DNS로 접근한다.
resource "aws_service_discovery_private_dns_namespace" "monitoring" {
  count       = var.monitoring_enabled ? 1 : 0
  name        = local.monitoring_service_discovery_namespace
  description = "Private DNS namespace for BADA monitoring services"
  vpc         = aws_vpc.main.id

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-monitoring-namespace" })
}

resource "aws_service_discovery_service" "prometheus" {
  count = var.monitoring_enabled ? 1 : 0
  name  = "prometheus"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.monitoring[0].id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-prometheus-discovery" })
}

# Grafana CloudWatch 데이터소스용 전용 읽기 권한.
# 애플리케이션 Task Role의 S3/SQS/Bedrock 권한을 모니터링 컨테이너에 노출하지 않는다.
resource "aws_iam_role" "monitoring_task" {
  count = var.monitoring_enabled ? 1 : 0
  name  = "${local.name_prefix}-monitoring-task-role"

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

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-monitoring-task-role" })
}

resource "aws_iam_role_policy" "monitoring_readonly" {
  count = var.monitoring_enabled ? 1 : 0
  name  = "${local.name_prefix}-monitoring-readonly"
  role  = aws_iam_role.monitoring_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:DescribeAlarms",
          "cloudwatch:GetMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics",
          "ec2:DescribeInstances",
          "ec2:DescribeRegions",
          "ec2:DescribeTags",
          "logs:DescribeLogGroups",
          "logs:GetQueryResults",
          "logs:StartQuery",
          "logs:StopQuery",
          "tag:GetResources"
        ]
        Resource = "*"
      }
    ]
  })
}

# EFS 파일시스템 (Grafana 데이터 영속화)
resource "aws_efs_file_system" "monitoring" {
  count          = var.monitoring_enabled ? 1 : 0
  creation_token = "${local.name_prefix}-monitoring-efs"
  encrypted      = true

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-monitoring-efs" })
}

resource "aws_efs_mount_target" "monitoring" {
  count           = var.monitoring_enabled ? length(aws_subnet.public) : 0
  file_system_id  = aws_efs_file_system.monitoring[0].id
  subnet_id       = aws_subnet.public[count.index].id
  security_groups = [aws_security_group.monitoring[0].id]
}

resource "aws_efs_access_point" "grafana" {
  count          = var.monitoring_enabled ? 1 : 0
  file_system_id = aws_efs_file_system.monitoring[0].id

  posix_user {
    gid = 472
    uid = 472
  }

  root_directory {
    path = "/grafana"
    creation_info {
      owner_gid   = 472
      owner_uid   = 472
      permissions = "0755"
    }
  }
}

# 보안 그룹 (모니터링 전용)
resource "aws_security_group" "monitoring" {
  count       = var.monitoring_enabled ? 1 : 0
  name        = "${local.name_prefix}-monitoring-sg"
  description = "Monitoring (Prometheus + Grafana) security group"
  vpc_id      = aws_vpc.main.id

  # Grafana 웹 UI (ALB에서만)
  ingress {
    description     = "Grafana from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Prometheus/Grafana communication inside the monitoring security group
  ingress {
    description = "Prometheus within monitoring"
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    self        = true
  }

  # EFS mount
  ingress {
    description = "NFS for EFS"
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    self        = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-monitoring-sg" })
}

# Prometheus ECS Task Definition
resource "aws_ecs_task_definition" "prometheus" {
  count                    = var.monitoring_enabled ? 1 : 0
  family                   = "${local.name_prefix}-prometheus"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.monitoring_task[0].arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.ecs_cpu_architecture
  }

  container_definitions = jsonencode([
    {
      name      = "prometheus-config"
      image     = "alpine:3.20"
      essential = false
      entryPoint = [
        "sh",
        "-c"
      ]
      command = [
        "set -eu; mkdir -p /config; printf '%s' \"$PROMETHEUS_CONFIG_BASE64\" | base64 -d > /config/prometheus.yml"
      ]
      environment = [
        { name = "PROMETHEUS_CONFIG_BASE64", value = local.prometheus_config_base64 }
      ]
      mountPoints = [
        { sourceVolume = "prometheus-config", containerPath = "/config" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/aws/ecs/${local.name_prefix}/prometheus"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "config"
        }
      }
    },
    {
      name         = "prometheus"
      image        = "prom/prometheus:v2.54.0"
      essential    = true
      portMappings = [{ containerPort = 9090, protocol = "tcp" }]
      dependsOn    = [{ containerName = "prometheus-config", condition = "SUCCESS" }]
      mountPoints = [
        { sourceVolume = "prometheus-data", containerPath = "/prometheus" },
        { sourceVolume = "prometheus-config", containerPath = "/etc/prometheus", readOnly = true }
      ]
      command = [
        "--config.file=/etc/prometheus/prometheus.yml",
        "--storage.tsdb.path=/prometheus",
        "--storage.tsdb.retention.time=3d",
        "--web.enable-lifecycle"
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/aws/ecs/${local.name_prefix}/prometheus"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "prometheus"
        }
      }
    }
  ])

  volume {
    name = "prometheus-config"
  }

  volume {
    name = "prometheus-data"
  }

  tags = local.common_tags
}

# Grafana ECS Task Definition
resource "aws_ecs_task_definition" "grafana" {
  count                    = var.monitoring_enabled ? 1 : 0
  family                   = "${local.name_prefix}-grafana"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.monitoring_task[0].arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.ecs_cpu_architecture
  }

  container_definitions = jsonencode([
    {
      name      = "grafana-config"
      image     = "alpine:3.20"
      essential = false
      entryPoint = [
        "sh",
        "-c"
      ]
      command = [
        "set -eu; mkdir -p /config/datasources /config/dashboards/json; printf '%s' \"$DATASOURCES_BASE64\" | base64 -d > /config/datasources/datasources.yml; printf '%s' \"$DASHBOARDS_CONFIG_BASE64\" | base64 -d > /config/dashboards/dashboards.yml; printf '%s' \"$OVERVIEW_DASHBOARD_BASE64\" | base64 -d > /config/dashboards/json/bada-overview.json"
      ]
      environment = [
        { name = "DATASOURCES_BASE64", value = local.grafana_datasources_base64 },
        { name = "DASHBOARDS_CONFIG_BASE64", value = local.grafana_dashboards_config_base64 },
        { name = "OVERVIEW_DASHBOARD_BASE64", value = local.grafana_overview_dashboard_base64 }
      ]
      mountPoints = [
        { sourceVolume = "grafana-config", containerPath = "/config" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/aws/ecs/${local.name_prefix}/grafana"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "config"
        }
      }
    },
    {
      name         = "grafana"
      image        = "grafana/grafana-oss:11.3.0"
      essential    = true
      portMappings = [{ containerPort = 3000, protocol = "tcp" }]
      dependsOn    = [{ containerName = "grafana-config", condition = "SUCCESS" }]
      mountPoints = [
        { sourceVolume = "grafana-data", containerPath = "/var/lib/grafana" },
        { sourceVolume = "grafana-config", containerPath = "/etc/grafana/provisioning", readOnly = true }
      ]
      environment = [
        { name = "GF_SERVER_ROOT_URL", value = "https://monitor.${var.domain_name}" },
        { name = "GF_USERS_ALLOW_SIGN_UP", value = "false" },
      ]
      secrets = [
        {
          name      = "GF_SECURITY_ADMIN_PASSWORD"
          valueFrom = aws_secretsmanager_secret.grafana_admin_password[0].arn
        },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/aws/ecs/${local.name_prefix}/grafana"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "grafana"
        }
      }
    }
  ])

  volume {
    name = "grafana-config"
  }

  volume {
    name = "grafana-data"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.monitoring[0].id
      root_directory     = "/"
      transit_encryption = "ENABLED"

      authorization_config {
        access_point_id = aws_efs_access_point.grafana[0].id
        iam             = "DISABLED"
      }
    }
  }

  tags = local.common_tags
}

# Prometheus ECS Service
resource "aws_ecs_service" "prometheus" {
  count           = var.monitoring_enabled ? 1 : 0
  name            = "${local.name_prefix}-prometheus"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.prometheus[0].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.monitoring[0].id]
    assign_public_ip = true
  }

  service_registries {
    registry_arn = aws_service_discovery_service.prometheus[0].arn
  }

  depends_on = [
    aws_efs_mount_target.monitoring,
    aws_cloudwatch_log_group.prometheus,
  ]

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-prometheus" })
}

# Grafana ECS Service
resource "aws_ecs_service" "grafana" {
  count           = var.monitoring_enabled ? 1 : 0
  name            = "${local.name_prefix}-grafana"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.grafana[0].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.monitoring[0].id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.grafana[0].arn
    container_name   = "grafana"
    container_port   = 3000
  }

  depends_on = [
    aws_efs_mount_target.monitoring,
    aws_cloudwatch_log_group.grafana,
    aws_lb_listener.https,
  ]

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-grafana" })
}

# Grafana Target Group
resource "aws_lb_target_group" "grafana" {
  count       = var.monitoring_enabled ? 1 : 0
  name        = "${local.name_prefix}-grafana-tg"
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id

  health_check {
    enabled             = true
    path                = "/api/health"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-grafana-tg" })
}

# ALB 라우팅: monitor.badasoft.com → Grafana
resource "aws_lb_listener_rule" "grafana" {
  count        = var.domain_name != "" && var.monitoring_enabled ? 1 : 0
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 5

  condition {
    host_header { values = ["monitor.${var.domain_name}"] }
  }
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.grafana[0].arn
  }
}

# Route 53: monitor.badasoft.com
resource "aws_route53_record" "monitor" {
  count   = var.domain_name != "" && var.monitoring_enabled ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "monitor.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "prometheus" {
  count             = var.monitoring_enabled ? 1 : 0
  name              = "/aws/ecs/${local.name_prefix}/prometheus"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "grafana" {
  count             = var.monitoring_enabled ? 1 : 0
  name              = "/aws/ecs/${local.name_prefix}/grafana"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_secretsmanager_secret" "grafana_admin_password" {
  count = var.monitoring_enabled ? 1 : 0
  name  = "${local.name_prefix}/grafana-admin-password"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-grafana-admin-password" })
}

resource "random_password" "grafana_admin" {
  count            = var.monitoring_enabled && var.grafana_admin_password == null ? 1 : 0
  length           = 24
  special          = true
  override_special = "!#$%&*+-=?@_"
}

resource "aws_secretsmanager_secret_version" "grafana_admin_password" {
  count         = var.monitoring_enabled ? 1 : 0
  secret_id     = aws_secretsmanager_secret.grafana_admin_password[0].id
  secret_string = var.grafana_admin_password != null ? var.grafana_admin_password : random_password.grafana_admin[0].result
}
