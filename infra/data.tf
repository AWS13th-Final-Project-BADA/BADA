# ─── Data: RDS / S3 / KMS / SQS / Secrets / SSM / Cognito ─────────────────
resource "aws_kms_key" "evidence" {
  description         = "${local.name_prefix} evidence encryption key"
  enable_key_rotation = true

  tags = local.common_tags
}

resource "aws_kms_alias" "evidence" {
  name          = "alias/${local.name_prefix}-evidence"
  target_key_id = aws_kms_key.evidence.key_id
}

resource "aws_s3_bucket" "evidence" {
  bucket = "${local.name_prefix}-evidence"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-evidence" })
}

resource "aws_s3_bucket" "report" {
  bucket = "${local.name_prefix}-report"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-report" })
}

resource "aws_s3_bucket_public_access_block" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "report" {
  bucket = aws_s3_bucket.report.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.evidence.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "report" {
  bucket = aws_s3_bucket.report.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.evidence.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_sqs_queue" "analysis_dlq" {
  name = "${local.name_prefix}-analysis-dlq"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-analysis-dlq" })
}

resource "aws_sqs_queue" "analysis" {
  name                       = "${local.name_prefix}-analysis"
  visibility_timeout_seconds = var.sqs_visibility_timeout_seconds
  receive_wait_time_seconds  = var.sqs_receive_wait_time_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.analysis_dlq.arn
    maxReceiveCount     = 5
  })

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-analysis" })
}

resource "aws_db_instance" "postgres" {
  identifier              = "${local.name_prefix}-postgres"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = var.db_instance_class
  allocated_storage       = var.db_allocated_storage
  db_name                 = "bada"
  username                = var.db_username
  password                = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  backup_retention_period = var.db_backup_retention_period
  deletion_protection     = var.db_deletion_protection
  skip_final_snapshot     = var.db_skip_final_snapshot
  final_snapshot_identifier = (
    var.db_skip_final_snapshot ? null : var.db_final_snapshot_identifier
  )
  apply_immediately   = var.db_apply_immediately
  publicly_accessible = false
  multi_az            = var.db_multi_az

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-postgres" })
}

resource "aws_cognito_user_pool" "main" {
  name = "${local.name_prefix}-user-pool"

  tags = local.common_tags
}

resource "aws_cognito_identity_provider" "google" {
  count = var.enable_google_identity_provider ? 1 : 0

  user_pool_id  = aws_cognito_user_pool.main.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    attributes_url                = "https://people.googleapis.com/v1/people/me?personFields="
    attributes_url_add_attributes = "true"
    authorize_scopes              = join(" ", var.cognito_oauth_scopes)
    authorize_url                 = "https://accounts.google.com/o/oauth2/v2/auth"
    client_id                     = var.google_oauth_client_id
    client_secret                 = var.google_oauth_client_secret
    oidc_issuer                   = "https://accounts.google.com"
    token_request_method          = "POST"
    token_url                     = "https://www.googleapis.com/oauth2/v4/token"
  }

  attribute_mapping = {
    email          = "email"
    email_verified = "email_verified"
    name           = "name"
    username       = "sub"
  }

  lifecycle {
    precondition {
      condition = (
        !var.enable_google_identity_provider ||
        (
          var.google_oauth_client_id != null &&
          var.google_oauth_client_secret != null &&
          try(trimspace(var.google_oauth_client_id), "") != "" &&
          try(trimspace(var.google_oauth_client_secret), "") != ""
        )
      )
      error_message = "Google OAuth client ID and client secret are required when enable_google_identity_provider is true."
    }
  }
}

resource "aws_cognito_user_pool_client" "app" {
  name                                 = "${local.name_prefix}-app-client"
  user_pool_id                         = aws_cognito_user_pool.main.id
  callback_urls                        = var.cognito_callback_urls
  logout_urls                          = var.cognito_logout_urls
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = var.cognito_oauth_scopes
  allowed_oauth_flows_user_pool_client = true
  supported_identity_providers = concat(
    ["COGNITO"],
    var.enable_google_identity_provider ? ["Google"] : []
  )
  prevent_user_existence_errors = "ENABLED"

  depends_on = [aws_cognito_identity_provider.google]
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = var.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "aws_s3_bucket" "alb_logs" {
  bucket = "${local.name_prefix}-alb-logs"
  tags   = merge(local.common_tags, { Name = "${local.name_prefix}-alb-logs" })
}

resource "aws_s3_bucket_lifecycle_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    id     = "expire-alb-access-logs"
    status = "Enabled"

    filter {
      prefix = "alb/"
    }

    expiration {
      days = var.alb_log_retention_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "logdelivery.elasticloadbalancing.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.alb_logs.arn}/alb/*"
      }
    ]
  })
}

resource "aws_secretsmanager_secret" "app" {
  name = "${local.name_prefix}/app-secrets"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-app-secrets" })
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    db_username  = var.db_username
    db_password  = var.db_password
    database_url = "postgresql+psycopg://${urlencode(var.db_username)}:${urlencode(var.db_password)}@${aws_db_instance.postgres.address}:5432/bada"
  })
}

resource "aws_ssm_parameter" "s3_evidence_bucket" {
  name  = "/${local.name_prefix}/s3/evidence_bucket"
  type  = "String"
  value = aws_s3_bucket.evidence.bucket

  tags = local.common_tags
}

resource "aws_ssm_parameter" "s3_report_bucket" {
  name  = "/${local.name_prefix}/s3/report_bucket"
  type  = "String"
  value = aws_s3_bucket.report.bucket

  tags = local.common_tags
}

resource "aws_ssm_parameter" "analysis_queue_url" {
  name  = "/${local.name_prefix}/sqs/analysis_queue_url"
  type  = "String"
  value = aws_sqs_queue.analysis.url

  tags = local.common_tags
}

resource "aws_ssm_parameter" "aws_region" {
  name  = "/${local.name_prefix}/config/aws_region"
  type  = "String"
  value = var.aws_region

  tags = local.common_tags
}

resource "aws_ssm_parameter" "cognito_user_pool_id" {
  name  = "/${local.name_prefix}/cognito/user_pool_id"
  type  = "String"
  value = aws_cognito_user_pool.main.id

  tags = local.common_tags
}

resource "aws_ssm_parameter" "cognito_client_id" {
  name  = "/${local.name_prefix}/cognito/client_id"
  type  = "String"
  value = aws_cognito_user_pool_client.app.id

  tags = local.common_tags
}

resource "aws_ssm_parameter" "cognito_domain" {
  name  = "/${local.name_prefix}/cognito/domain"
  type  = "String"
  value = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com/"

  tags = local.common_tags
}

resource "aws_ssm_parameter" "cognito_redirect_uri" {
  name  = "/${local.name_prefix}/cognito/redirect_uri"
  type  = "String"
  value = var.cognito_callback_urls[0]

  tags = local.common_tags
}

resource "aws_ssm_parameter" "cognito_logout_uri" {
  name  = "/${local.name_prefix}/cognito/logout_uri"
  type  = "String"
  value = var.cognito_logout_urls[0]

  tags = local.common_tags
}

resource "aws_ssm_parameter" "cognito_scopes" {
  name  = "/${local.name_prefix}/cognito/scopes"
  type  = "String"
  value = join(" ", var.cognito_oauth_scopes)

  tags = local.common_tags
}
