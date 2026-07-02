variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "bada"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "mcp_operator_principal_arns" {
  description = "IAM principal ARNs allowed to assume the read-only CloudWatch MCP role"
  type        = list(string)
  default     = ["arn:aws:iam::165749212250:user/awsuser"]

  validation {
    condition     = length(var.mcp_operator_principal_arns) > 0
    error_message = "mcp_operator_principal_arns must contain at least one trusted IAM principal ARN."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the main VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "bada_admin"
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_backup_retention_period" {
  description = "RDS automated backup retention period in days"
  type        = number
  default     = 7
}

variable "db_deletion_protection" {
  description = "Whether RDS deletion protection is enabled"
  type        = bool
  default     = true
}

variable "db_skip_final_snapshot" {
  description = "Whether to skip the final RDS snapshot on deletion"
  type        = bool
  default     = false
}

variable "db_final_snapshot_identifier" {
  description = "Final RDS snapshot identifier used when skip_final_snapshot is false"
  type        = string
  default     = "bada-dev-postgres-final-snapshot"
}

variable "db_apply_immediately" {
  description = "Whether RDS configuration changes are applied immediately"
  type        = bool
  default     = true
}

variable "enable_rehearsal_multiaz_db" {
  description = "Create a separate encrypted Multi-AZ rehearsal RDS instance without touching the current primary DB."
  type        = bool
  default     = true
}

variable "rehearsal_db_identifier" {
  description = "Identifier for the separate rehearsal RDS instance used for Multi-AZ cutover practice."
  type        = string
  default     = "bada-dev-postgres-multiaz"
}

variable "rehearsal_db_kms_key_arn" {
  description = "Optional KMS key ARN for the rehearsal encrypted RDS instance. Null uses the default AWS managed key."
  type        = string
  default     = null
  nullable    = true
}

variable "rehearsal_db_skip_final_snapshot" {
  description = "Whether to skip the final snapshot when deleting the rehearsal RDS instance."
  type        = bool
  default     = false
}

variable "rehearsal_db_final_snapshot_identifier" {
  description = "Final snapshot identifier for the rehearsal RDS instance when skip_final_snapshot is false."
  type        = string
  default     = "bada-dev-postgres-multiaz-final-snapshot"
}

variable "use_rehearsal_multiaz_db_as_app_db" {
  description = "Point app DATABASE_URL at the rehearsal Multi-AZ DB after restore/canary validation. Set false to roll back to the original DB."
  type        = bool
  default     = true
}

variable "app_port" {
  description = "Backend container application port"
  type        = number
  default     = 8000
}

variable "cognito_domain_prefix" {
  description = "Globally unique Cognito Hosted UI domain prefix"
  type        = string
  default     = "bada-dev-165749212250"
}

variable "cognito_callback_urls" {
  description = "Allowed OAuth callback URLs for the Cognito App Client"
  type        = list(string)
  default     = ["http://localhost:8000/auth/cognito/callback"]
}

variable "cognito_logout_urls" {
  description = "Allowed sign-out URLs for the Cognito App Client"
  type        = list(string)
  default     = ["http://localhost:8000/"]
}

variable "cognito_oauth_scopes" {
  description = "Allowed OAuth scopes for the Cognito App Client"
  type        = list(string)
  default     = ["openid", "email", "profile"]
}

variable "enable_google_identity_provider" {
  description = "Whether to configure Google as a Cognito federated identity provider"
  type        = bool
  default     = false
}

variable "google_oauth_client_id" {
  description = "Google OAuth 2.0 client ID used by Cognito"
  type        = string
  default     = null
  nullable    = true
}

variable "google_oauth_client_secret" {
  description = "Google OAuth 2.0 client secret used by Cognito"
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 14
}

variable "alb_log_retention_days" {
  description = "ALB access log retention period in S3"
  type        = number
  default     = 30

  validation {
    condition     = var.alb_log_retention_days >= 7
    error_message = "alb_log_retention_days must be at least 7 days."
  }
}

variable "sqs_visibility_timeout_seconds" {
  description = "Time an in-flight analysis message remains hidden. 15 minutes covers the worker transcription timeout with a buffer."
  type        = number
  default     = 900

  validation {
    condition     = var.sqs_visibility_timeout_seconds >= 0 && var.sqs_visibility_timeout_seconds <= 43200
    error_message = "sqs_visibility_timeout_seconds must be between 0 and 43200 seconds."
  }
}

variable "sqs_receive_wait_time_seconds" {
  description = "SQS long-polling wait time for worker receive requests."
  type        = number
  default     = 20

  validation {
    condition     = var.sqs_receive_wait_time_seconds >= 0 && var.sqs_receive_wait_time_seconds <= 20
    error_message = "sqs_receive_wait_time_seconds must be between 0 and 20 seconds."
  }
}

variable "alarm_actions" {
  description = "Additional alarm action ARNs. Keep empty unless the team already owns a separate notification target."
  type        = list(string)
  default     = []
}

variable "alarm_email_endpoints" {
  description = "Email addresses subscribed to the Terraform-managed SNS topic for CloudWatch alarm notifications. Each address must confirm the SNS subscription email."
  type        = list(string)
  default     = []
}

variable "api_container_image" {
  description = "Backend API container image URI"
  type        = string
  default     = "replace-me"
}

variable "worker_container_image" {
  description = "Worker container image URI"
  type        = string
  default     = "replace-me"
}

variable "frontend_container_image" {
  description = "Frontend container image URI"
  type        = string
  default     = "replace-me"
}

variable "backend_task_cpu" {
  description = "Backend ECS task CPU units"
  type        = number
  default     = 256
}

variable "backend_task_memory" {
  description = "Backend ECS task memory in MiB"
  type        = number
  default     = 512
}

variable "backend_desired_count" {
  description = "Initial desired count for backend ECS service. Keep 0 until an image is pushed."
  type        = number
  default     = 0
}

variable "worker_task_cpu" {
  description = "Worker ECS task CPU units"
  type        = number
  default     = 1024
}

variable "worker_task_memory" {
  description = "Worker ECS task memory in MiB"
  type        = number
  default     = 2048
}

variable "worker_desired_count" {
  description = "Initial desired count for worker ECS service. Keep 0 until the queue consumer is ready."
  type        = number
  default     = 0
}

variable "frontend_task_cpu" {
  description = "Frontend ECS task CPU units"
  type        = number
  default     = 256
}

variable "frontend_task_memory" {
  description = "Frontend ECS task memory in MiB"
  type        = number
  default     = 512
}

variable "frontend_desired_count" {
  description = "Desired count for the frontend ECS service. Keep 0 until the first image is pushed."
  type        = number
  default     = 0
}

variable "ecs_cpu_architecture" {
  description = "CPU architecture for ECS Fargate tasks. ARM64 is cost-efficient and matches Apple Silicon local builds."
  type        = string
  default     = "ARM64"

  validation {
    condition     = contains(["X86_64", "ARM64"], var.ecs_cpu_architecture)
    error_message = "ecs_cpu_architecture must be either X86_64 or ARM64."
  }
}

variable "backend_xray_enabled" {
  description = "Enable AWS X-Ray tracing for the Backend ECS task. Keep false until the Backend X-Ray middleware imports a supported SDK integration."
  type        = bool
  default     = false
}

variable "worker_xray_enabled" {
  description = "Enable AWS X-Ray tracing for the Worker ECS task."
  type        = bool
  default     = true
}

variable "xray_daemon_image" {
  description = "AWS X-Ray daemon sidecar image used by Backend and Worker ECS tasks."
  type        = string
  default     = "public.ecr.aws/xray/aws-xray-daemon:latest"
}

variable "database_auto_create" {
  description = "Whether the backend should auto-create database tables at startup"
  type        = bool
  default     = true
}

variable "database_pool_size" {
  description = "Backend database connection pool size"
  type        = number
  default     = 5
}

variable "database_max_overflow" {
  description = "Backend database connection pool max overflow"
  type        = number
  default     = 10
}

variable "backend_provider_mode" {
  description = "Backend provider mode. Use local/mock by default to control Bedrock/OCR cost."
  type        = string
  default     = "local"
}

variable "backend_auth_mode" {
  description = "Backend authentication mode"
  type        = string
  default     = "demo"

  validation {
    condition     = contains(["demo", "oauth", "cognito"], var.backend_auth_mode)
    error_message = "backend_auth_mode must be demo, oauth, or cognito."
  }
}

variable "backend_app_base_url" {
  description = "Frontend URL used after authentication callbacks"
  type        = string
  default     = "http://localhost:3000"
}

# ---- 소셜 OAuth (Cognito 제거, 구글/카카오/네이버 직접) ----
# 값은 prod tfvars / CI Secret(TF_VAR_*)으로 주입. git 커밋 금지. (db_password와 동일하게 필수)
variable "google_client_id" {
  description = "Google OAuth 2.0 client ID for backend social login"
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth 2.0 client secret for backend social login"
  type        = string
  sensitive   = true
}

variable "kakao_rest_api_key" {
  description = "Kakao REST API key for social login"
  type        = string
  sensitive   = true
}

variable "kakao_client_secret" {
  description = "Kakao client secret for social login"
  type        = string
  sensitive   = true
}

variable "naver_client_id" {
  description = "Naver OAuth client ID for social login"
  type        = string
  sensitive   = true
}

variable "naver_client_secret" {
  description = "Naver OAuth client secret for social login"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "Secret for signing/verifying backend-issued HS256 JWT (social OAuth)"
  type        = string
  sensitive   = true
}

variable "backend_cors_allowed_origins" {
  description = "Origins allowed to call the Backend API"
  type        = list(string)
  default     = ["http://localhost:3000", "http://localhost:8000"]
}

variable "backend_ai_chat_mode" {
  description = "Backend AI chat mode"
  type        = string
  default     = "mock"
}

variable "backend_embedding_mode" {
  description = "Backend embedding mode"
  type        = string
  default     = "mock"
}

variable "backend_transcription_dispatch_mode" {
  description = "How backend dispatches audio transcription jobs. Use inline for MVP demo until the SQS worker consumer is ready."
  type        = string
  default     = "inline"

  validation {
    condition     = contains(["inline", "sqs"], var.backend_transcription_dispatch_mode)
    error_message = "backend_transcription_dispatch_mode must be either inline or sqs."
  }
}

variable "backend_transcribe_mode" {
  description = "Backend audio transcription provider mode. Defaults to provider mode when empty."
  type        = string
  default     = ""

  validation {
    condition     = contains(["", "local", "aws"], var.backend_transcribe_mode)
    error_message = "backend_transcribe_mode must be empty, local, or aws."
  }
}

variable "worker_provider_mode" {
  description = "Worker provider mode"
  type        = string
  default     = "local"
}

variable "worker_transcribe_mode" {
  description = "Worker audio transcription provider mode. Defaults to provider mode when empty."
  type        = string
  default     = ""

  validation {
    condition     = contains(["", "local", "aws"], var.worker_transcribe_mode)
    error_message = "worker_transcribe_mode must be empty, local, or aws."
  }
}

variable "worker_translate_mode" {
  description = "Worker translation mode"
  type        = string
  default     = "local"
}

variable "worker_structured_engine" {
  description = "Worker structured OCR engine"
  type        = string
  default     = "vision"
}

variable "retention_days" {
  description = "Application data retention period in days"
  type        = number
  default     = 90
}

variable "github_owner" {
  description = "GitHub organization or user that owns the repository"
  type        = string
  default     = "AWS13th-Final-Project-BADA"
}

variable "github_repository" {
  description = "GitHub repository name allowed to assume the deploy role"
  type        = string
  default     = "BADA"
}

variable "github_deploy_branch" {
  description = "GitHub branch allowed to deploy the dev environment"
  type        = string
  default     = "develop"
}


variable "domain_name" {
  description = "Root domain name (e.g., badasoft.com). Leave empty to skip HTTPS/Route53 setup."
  type        = string
  default     = ""
}

variable "frontend_enabled" {
  description = "Enable frontend ECR, target group, and ALB routing. Set true when frontend is ready to deploy."
  type        = bool
  default     = false
}


variable "monitoring_enabled" {
  description = "Enable Prometheus + Grafana monitoring stack"
  type        = bool
  default     = false
}

variable "grafana_admin_password" {
  description = "Optional Grafana administrator password override. When null, Terraform generates one and stores it in Secrets Manager."
  type        = string
  default     = null
  nullable    = true
  sensitive   = true

  validation {
    condition     = var.grafana_admin_password == null ? true : length(var.grafana_admin_password) >= 12
    error_message = "grafana_admin_password must contain at least 12 characters when provided."
  }
}

# ---- ECS Auto Scaling (#4) ----
# Backend: 평균 CPU 기반 Target Tracking. Worker: 태스크당 SQS 적체 기반 Target Tracking.
# 종료(7/10) 시 *_autoscaling_enabled=false 로 target/policy 제거 후 desired_count 고정.

variable "backend_autoscaling_enabled" {
  description = "Enable Application Auto Scaling for the Backend ECS service (CPU target tracking)."
  type        = bool
  default     = true
}

variable "backend_min_capacity" {
  description = "Minimum backend task count under Auto Scaling."
  type        = number
  default     = 1
}

variable "backend_max_capacity" {
  description = "Maximum backend task count under Auto Scaling."
  type        = number
  default     = 3

  validation {
    condition     = var.backend_max_capacity >= var.backend_min_capacity
    error_message = "backend_max_capacity must be >= backend_min_capacity."
  }
}

variable "backend_cpu_target" {
  description = "Target average CPU utilization (%) for backend scaling."
  type        = number
  default     = 70

  validation {
    condition     = var.backend_cpu_target > 0 && var.backend_cpu_target <= 100
    error_message = "backend_cpu_target must be between 1 and 100."
  }
}

variable "worker_autoscaling_enabled" {
  description = "Enable Application Auto Scaling for the Worker ECS service (SQS backlog target tracking)."
  type        = bool
  default     = true
}

variable "worker_min_capacity" {
  description = "Minimum worker task count under Auto Scaling. Keep >=1 so backlog-per-task math never divides by zero."
  type        = number
  default     = 1

  validation {
    condition     = var.worker_min_capacity >= 1
    error_message = "worker_min_capacity must be at least 1 to keep backlog-per-task metric math valid."
  }
}

variable "worker_max_capacity" {
  description = "Maximum worker task count under Auto Scaling."
  type        = number
  default     = 3

  validation {
    condition     = var.worker_max_capacity >= var.worker_min_capacity
    error_message = "worker_max_capacity must be >= worker_min_capacity."
  }
}

variable "worker_backlog_target_per_task" {
  description = "Target number of visible SQS messages per running worker task. Above this, Auto Scaling adds workers."
  type        = number
  default     = 5

  validation {
    condition     = var.worker_backlog_target_per_task > 0
    error_message = "worker_backlog_target_per_task must be greater than 0."
  }
}

variable "autoscaling_scale_out_cooldown" {
  description = "Seconds to wait after a scale-out before another scale-out."
  type        = number
  default     = 60
}

variable "autoscaling_scale_in_cooldown" {
  description = "Seconds to wait after a scale-in before another scale-in. Longer than scale-out to avoid flapping."
  type        = number
  default     = 300
}
