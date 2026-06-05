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
