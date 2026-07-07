variable "aws_region" {
  type    = string
  default = "ap-northeast-2"
}

variable "account_id" {
  description = "AWS 계정 ID (S3 버킷 이름 유일화용)"
  type        = string
}

variable "vpc_id" {
  description = "runner를 둘 VPC (perf VPC 권장). ALB는 public이라 인터넷 경유 호출."
  type        = string
}

variable "image_uri" {
  description = "runner 이미지 URI. 비우면 이 repo의 :latest 사용."
  type        = string
  default     = ""
}

variable "runner_cpu" {
  description = "runner 태스크 CPU (1024=1vCPU)"
  type        = number
  default     = 1024
}

variable "runner_memory" {
  description = "runner 태스크 메모리 MiB"
  type        = number
  default     = 2048
}
