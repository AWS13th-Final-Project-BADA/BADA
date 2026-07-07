output "ecr_repository_url" {
  value = aws_ecr_repository.runner.repository_url
}

output "task_definition_arn" {
  value = aws_ecs_task_definition.runner.arn
}

output "task_definition_family" {
  value = aws_ecs_task_definition.runner.family
}

output "security_group_id" {
  value = aws_security_group.runner.id
}

output "log_group" {
  value = aws_cloudwatch_log_group.runner.name
}

output "results_bucket" {
  value = aws_s3_bucket.results.bucket
}
