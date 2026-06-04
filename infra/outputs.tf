output "s3_bucket_name" {
  value = aws_s3_bucket.evidence.bucket
}

output "kms_key_arn" {
  value = aws_kms_key.evidence.arn
}

output "sqs_queue_url" {
  value = aws_sqs_queue.analysis.url
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
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
