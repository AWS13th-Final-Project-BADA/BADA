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

variable "app_port" {
  description = "Backend container application port"
  type        = number
  default     = 8000
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 14
}

variable "alarm_actions" {
  description = "SNS topic ARNs or other alarm action ARNs. Keep empty for console-only alarms."
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
  default     = 256
}

variable "worker_task_memory" {
  description = "Worker ECS task memory in MiB"
  type        = number
  default     = 512
}

variable "worker_desired_count" {
  description = "Initial desired count for worker ECS service. Keep 0 until the queue consumer is ready."
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

variable "worker_provider_mode" {
  description = "Worker provider mode"
  type        = string
  default     = "local"
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
