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

output "ssm_db_access_instance_id" {
  value = aws_instance.ssm_db_access.id
}

output "ssm_db_port_forward_command" {
  value = "aws ssm start-session --target ${aws_instance.ssm_db_access.id} --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters '{\"host\":[\"${aws_db_instance.postgres.address}\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"15432\"]}'"
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.main.id
}

output "cognito_app_client_id" {
  value = aws_cognito_user_pool_client.app.id
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

output "backend_task_definition_arn" {
  value = aws_ecs_task_definition.backend.arn
}

output "worker_task_definition_arn" {
  value = aws_ecs_task_definition.worker.arn
}

output "backend_ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "worker_ecr_repository_url" {
  value = aws_ecr_repository.worker.repository_url
}

output "secrets_manager_secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}
