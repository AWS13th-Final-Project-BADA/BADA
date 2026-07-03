output "s3_bucket_name" {
  value = aws_s3_bucket.evidence.bucket
}

output "report_bucket_name" {
  value = aws_s3_bucket.report.bucket
}

output "kms_key_arn" {
  value = aws_kms_key.evidence.arn
}

output "sqs_queue_url" {
  value = aws_sqs_queue.analysis.url
}

output "sqs_dlq_url" {
  value = aws_sqs_queue.analysis_dlq.url
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}

output "rds_rehearsal_endpoint" {
  value = try(aws_db_instance.postgres_rehearsal[0].address, null)
}

output "ssm_db_access_instance_id" {
  value = aws_instance.ssm_db_access.id
}

output "ssm_db_port_forward_command" {
  value = "aws ssm start-session --target ${aws_instance.ssm_db_access.id} --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters '{\"host\":[\"${aws_db_instance.postgres.address}\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"15432\"]}'"
}

output "ssm_db_rehearsal_port_forward_command" {
  value = try("aws ssm start-session --target ${aws_instance.ssm_db_access.id} --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters '{\"host\":[\"${aws_db_instance.postgres_rehearsal[0].address}\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"15433\"]}'", null)
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.main.id
}

output "cognito_app_client_id" {
  value = aws_cognito_user_pool_client.app.id
}

output "cognito_domain" {
  value = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com/"
}

output "cognito_redirect_uri" {
  value = var.cognito_callback_urls[0]
}

output "cognito_logout_uri" {
  value = var.cognito_logout_urls[0]
}

output "cognito_oauth_scopes" {
  value = join(" ", var.cognito_oauth_scopes)
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "backend_target_group_arn" {
  value = aws_lb_target_group.backend.arn
}

output "backend_ecs_service_name" {
  value = aws_ecs_service.backend.name
}

output "worker_ecs_service_name" {
  value = aws_ecs_service.worker.name
}

output "frontend_ecs_service_name" {
  value = try(aws_ecs_service.frontend[0].name, null)
}

output "backend_task_definition_arn" {
  value = aws_ecs_task_definition.backend.arn
}

output "worker_task_definition_arn" {
  value = aws_ecs_task_definition.worker.arn
}

output "frontend_task_definition_arn" {
  value = try(aws_ecs_task_definition.frontend[0].arn, null)
}

output "backend_ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "worker_ecr_repository_url" {
  value = aws_ecr_repository.worker.repository_url
}

output "frontend_ecr_repository_url" {
  value = try(aws_ecr_repository.frontend[0].repository_url, null)
}

output "secrets_manager_secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}

output "github_actions_deploy_role_arn" {
  value = aws_iam_role.github_actions_deploy.arn
}

output "github_actions_plan_role_arn" {
  value = aws_iam_role.github_actions_plan.arn
}

output "mcp_cloudwatch_readonly_role_arn" {
  value = aws_iam_role.mcp_cloudwatch_readonly.arn
}

output "alarm_sns_topic_arn" {
  value = aws_sns_topic.alarms.arn
}

output "monitoring_url" {
  value = var.monitoring_enabled && var.domain_name != "" ? "https://monitor.${var.domain_name}" : null
}

output "prometheus_private_dns_name" {
  value = var.monitoring_enabled ? "prometheus.${local.monitoring_service_discovery_namespace}" : null
}

output "nat_gateway_id" {
  description = "NAT Gateway ID (nat_gateway_enabled=true일 때). private subnet egress 경로."
  value       = try(aws_nat_gateway.main[0].id, null)
}

output "nat_gateway_public_ip" {
  description = "NAT Gateway의 고정 public IP(EIP). private subnet에서 나가는 egress의 출발지 IP."
  value       = try(aws_eip.nat[0].public_ip, null)
}

output "ecs_service_subnet_tier" {
  description = "현재 ECS 서비스가 배치된 subnet tier (private/public)."
  value       = var.ecs_in_private_subnets ? "private" : "public"
}
