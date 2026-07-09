# ─── 모니터링 인프라: Prometheus + Grafana (ECS Fargate) ────────────────────

locals {
  monitoring_service_discovery_namespace = "${local.name_prefix}.local"
  prometheus_config_base64 = base64encode(templatefile(
    "${path.module}/../monitoring/prometheus/prometheus.yml",
    {
      domain_name                 = var.domain_name
      service_discovery_namespace = local.monitoring_service_discovery_namespace
      # prod backend를 공인 ALB로 스크랩(크로스 환경). prod worker는 크로스-VPC라 CloudWatch로 관측.
      prod_backend_target_enabled = var.prod_monitoring_enabled && var.prod_domain_name != ""
      prod_domain_name            = var.prod_domain_name
    }
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
  grafana_infrastructure_dashboard_base64 = base64encode(templatefile(
    "${path.module}/../monitoring/grafana/provisioning/dashboards/json/bada-infrastructure.json",
    {
      aws_region      = var.aws_region
      ecs_cluster     = aws_ecs_cluster.main.name
      backend_service = aws_ecs_service.backend.name
      worker_service  = aws_ecs_service.worker.name
      rds_instance_id = aws_db_instance.postgres.identifier
      alb_arn_suffix  = aws_lb.main.arn_suffix
      sqs_queue_name  = aws_sqs_queue.analysis.name
      sqs_dlq_name    = aws_sqs_queue.analysis_dlq.name
    }
  ))
  # 크로스 환경(prod) 대시보드: prod는 별도 state이므로 리소스를 이름으로 참조한다.
  # ALB arn_suffix만 비결정적이라 data source로 조회(prod_monitoring_enabled일 때만).
  grafana_prod_infrastructure_dashboard_base64 = base64encode(templatefile(
    "${path.module}/../monitoring/grafana/provisioning/dashboards/json/bada-prod-infrastructure.json",
    {
      aws_region      = var.aws_region
      ecs_cluster     = var.prod_ecs_cluster_name
      backend_service = var.prod_backend_service_name
      worker_service  = var.prod_worker_service_name
      rds_instance_id = var.prod_rds_instance_id
      alb_arn_suffix  = try(data.aws_lb.prod[0].arn_suffix, "")
      sqs_queue_name  = var.prod_sqs_queue_name
      sqs_dlq_name    = var.prod_sqs_dlq_name
    }
  ))
  grafana_backend_dashboard_base64 = filebase64(
    "${path.module}/../monitoring/grafana/provisioning/dashboards/json/bada-backend.json"
  )
  grafana_worker_dashboard_base64 = base64encode(templatefile(
    "${path.module}/../monitoring/grafana/provisioning/dashboards/json/bada-worker.json",
    {
      aws_region     = var.aws_region
      sqs_queue_name = aws_sqs_queue.analysis.name
      sqs_dlq_name   = aws_sqs_queue.analysis_dlq.name
    }
  ))
  grafana_alerting_contactpoints_base64 = base64encode(templatefile(
    "${path.module}/../monitoring/grafana/provisioning/alerting/contactpoints.yml",
    {
      sns_topic_arn = aws_sns_topic.alarms.arn
      aws_region    = var.aws_region
    }
  ))
  grafana_alerting_rules_base64 = base64encode(templatefile(
    "${path.module}/../monitoring/grafana/provisioning/alerting/rules.yml",
    {
      rds_instance_id = aws_db_instance.postgres.identifier
      aws_region      = var.aws_region
    }
  ))
  grafana_alerting_policies_base64 = filebase64(
    "${path.module}/../monitoring/grafana/provisioning/alerting/policies.yml"
  )
}

# prod ALB arn_suffix 조회 — CloudWatch ALB 지표(LoadBalancer dimension)용.
# prod_monitoring_enabled=true일 때만 조회하며, prod 스택의 ALB가 존재해야 한다.
# 종료 시 false로 되돌리면 조회가 사라지고 prod ALB 패널은 무데이터가 된다.
data "aws_lb" "prod" {
  count = var.prod_monitoring_enabled && var.prod_alb_name != "" ? 1 : 0
  name  = var.prod_alb_name
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

resource "aws_service_discovery_service" "worker" {
  count = var.monitoring_enabled ? 1 : 0
  name  = "worker"

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

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-worker-discovery" })
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
          "ecs:DescribeClusters",
          "ecs:DescribeServices",
          "ecs:DescribeTasks",
          "ecs:ListClusters",
          "ecs:ListServices",
          "ecs:ListTasks",
          "logs:DescribeLogGroups",
          "logs:GetQueryResults",
          "logs:StartQuery",
          "logs:StopQuery",
          "oam:ListSinks",
          "tag:GetResources"
        ]
        Resource = "*"
      }
    ]
  })
}

# Grafana Alert를 기존 알람 SNS Topic으로 발행하기 위한 최소권한.
# 모니터링 Task Role이 해당 Topic에만 sns:Publish 하도록 스코프한다.
# (Grafana Contact Point/Alert rule 연결은 모니터링 담당이 임계치 전달 후 구성)
resource "aws_iam_role_policy" "monitoring_sns_publish" {
  count = var.monitoring_enabled ? 1 : 0
  name  = "${local.name_prefix}-monitoring-sns-publish"
  role  = aws_iam_role.monitoring_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = aws_sns_topic.alarms.arn
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
        "set -eu; mkdir -p /config/datasources /config/dashboards/json /config/alerting; printf '%s' \"$DATASOURCES_BASE64\" | base64 -d > /config/datasources/datasources.yml; printf '%s' \"$DASHBOARDS_CONFIG_BASE64\" | base64 -d > /config/dashboards/dashboards.yml; printf '%s' \"$OVERVIEW_DASHBOARD_BASE64\" | base64 -d > /config/dashboards/json/bada-overview.json; printf '%s' \"$INFRA_DASHBOARD_BASE64\" | base64 -d > /config/dashboards/json/bada-infrastructure.json; printf '%s' \"$PROD_INFRA_DASHBOARD_BASE64\" | base64 -d > /config/dashboards/json/bada-prod-infrastructure.json; printf '%s' \"$BACKEND_DASHBOARD_BASE64\" | base64 -d > /config/dashboards/json/bada-backend.json; printf '%s' \"$WORKER_DASHBOARD_BASE64\" | base64 -d > /config/dashboards/json/bada-worker.json; printf '%s' \"$ALERTING_CONTACTPOINTS_BASE64\" | base64 -d > /config/alerting/contactpoints.yml; printf '%s' \"$ALERTING_RULES_BASE64\" | base64 -d > /config/alerting/rules.yml; printf '%s' \"$ALERTING_POLICIES_BASE64\" | base64 -d > /config/alerting/policies.yml"
      ]
      environment = [
        { name = "DATASOURCES_BASE64", value = local.grafana_datasources_base64 },
        { name = "DASHBOARDS_CONFIG_BASE64", value = local.grafana_dashboards_config_base64 },
        { name = "OVERVIEW_DASHBOARD_BASE64", value = local.grafana_overview_dashboard_base64 },
        { name = "INFRA_DASHBOARD_BASE64", value = local.grafana_infrastructure_dashboard_base64 },
        { name = "PROD_INFRA_DASHBOARD_BASE64", value = local.grafana_prod_infrastructure_dashboard_base64 },
        { name = "BACKEND_DASHBOARD_BASE64", value = local.grafana_backend_dashboard_base64 },
        { name = "WORKER_DASHBOARD_BASE64", value = local.grafana_worker_dashboard_base64 },
        { name = "ALERTING_CONTACTPOINTS_BASE64", value = local.grafana_alerting_contactpoints_base64 },
        { name = "ALERTING_RULES_BASE64", value = local.grafana_alerting_rules_base64 },
        { name = "ALERTING_POLICIES_BASE64", value = local.grafana_alerting_policies_base64 }
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
    subnets          = local.ecs_service_subnets
    security_groups  = [aws_security_group.monitoring[0].id]
    assign_public_ip = local.ecs_assign_public_ip
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
    subnets          = local.ecs_service_subnets
    security_groups  = [aws_security_group.monitoring[0].id]
    assign_public_ip = local.ecs_assign_public_ip
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
