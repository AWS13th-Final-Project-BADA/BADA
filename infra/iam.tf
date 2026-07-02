# ─── IAM: Roles / Policies ──────────────────────────────────────────────────
resource "aws_iam_role" "ssm_db_access" {
  name = "${local.name_prefix}-ssm-db-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ssm_db_access_core" {
  role       = aws_iam_role.ssm_db_access.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.name_prefix}-ecs-task-execution-role"

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

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_task_execution_config_read" {
  name = "${local.name_prefix}-ecs-task-execution-config-read"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = concat(
          [aws_secretsmanager_secret.app.arn],
          var.monitoring_enabled ? [aws_secretsmanager_secret.grafana_admin_password[0].arn] : []
        )
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          aws_ssm_parameter.s3_evidence_bucket.arn,
          aws_ssm_parameter.s3_report_bucket.arn,
          aws_ssm_parameter.analysis_queue_url.arn,
          aws_ssm_parameter.aws_region.arn,
          aws_ssm_parameter.cognito_user_pool_id.arn,
          aws_ssm_parameter.cognito_client_id.arn
        ]
      }
    ]
  })
}

# ─── ECS Task Roles: Backend / Worker 분리 (#13) ────────────────────────────
#
# 기존 단일 ecs_task 역할을 서비스별 최소권한 역할 2개로 분리한다.
# 권한 경계는 코드에서 확인한 실제 사용 패턴 기준:
#   Backend  = producer   : SQS SendMessage / 증거 업로드·삭제 / Bedrock(chat) / Translate
#   Worker   = consumer   : SQS Receive·Delete / 증거 읽기 / 리포트 쓰기 / Bedrock·Transcribe·Translate
#
# 공통(둘 다 부여):
#   - KMS(evidence key) : SSE-KMS 객체 read/write
#   - X-Ray             : 분산 추적 세그먼트 전송
#   - Secrets(app)      : 런타임 시크릿 조회
#   - ssmmessages       : ECS Exec (enable_execute_command=true)
#   - SSM GetParameter  : 비민감 설정값 조회
#
# 롤아웃 주의(인프라 담당): 이 변경은 기존 ecs_task 역할을 제거하고 신규 역할 2개를
# 생성한다. apply 후 Backend/Worker Task Definition을 신규 역할로 재등록·재배포해야
# 실행 중 태스크가 새 역할을 사용한다. (ECS 서비스는 ignore_changes=[task_definition]
# 이므로 CD 재배포로 반영) 구 역할은 신규 Task Definition 배포 완료 후 정리된다.

locals {
  # 두 태스크 역할이 공유하는 SSM 파라미터 목록.
  ecs_task_ssm_parameter_arns = [
    aws_ssm_parameter.s3_evidence_bucket.arn,
    aws_ssm_parameter.s3_report_bucket.arn,
    aws_ssm_parameter.analysis_queue_url.arn,
    aws_ssm_parameter.aws_region.arn,
    aws_ssm_parameter.cognito_user_pool_id.arn,
    aws_ssm_parameter.cognito_client_id.arn
  ]

  ecs_task_assume_role_policy = jsonencode({
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
}

# ── Backend Task Role ───────────────────────────────────────────────────────
resource "aws_iam_role" "ecs_task_backend" {
  name               = "${local.name_prefix}-ecs-task-backend-role"
  assume_role_policy = local.ecs_task_assume_role_policy

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ecs-task-backend-role" })
}

resource "aws_iam_role_policy" "ecs_task_backend" {
  name = "${local.name_prefix}-ecs-task-backend-access"
  role = aws_iam_role.ecs_task_backend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListEvidenceAndReportBuckets"
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = [
          aws_s3_bucket.evidence.arn,
          aws_s3_bucket.report.arn
        ]
      },
      {
        # 증거: 업로드(Put)·조회(Get)·회원탈퇴/보관기간 만료 삭제(Delete)
        Sid      = "EvidenceObjectReadWriteDelete"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = ["${aws_s3_bucket.evidence.arn}/*"]
      },
      {
        # 리포트: 다운로드 제공(Get)·삭제(Delete). 생성(Put)은 Worker 담당.
        Sid      = "ReportObjectReadDelete"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:DeleteObject"]
        Resource = ["${aws_s3_bucket.report.arn}/*"]
      },
      {
        Sid      = "EvidenceKmsUse"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey"]
        Resource = aws_kms_key.evidence.arn
      },
      {
        # Producer: 분석/전사 작업 메시지 발행만. Receive/Delete 불가.
        Sid    = "SqsProduce"
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueUrl",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.analysis.arn
      },
      {
        # AI 챗봇/문장화(Bedrock) + 실시간 번역(Amazon Translate).
        Sid    = "BedrockAndTranslate"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "translate:TranslateText"
        ]
        Resource = "*"
      },
      {
        Sid    = "XRayWrite"
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
          "xray:GetSamplingStatisticSummaries"
        ]
        Resource = "*"
      },
      {
        Sid      = "AppSecretRead"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.app.arn
      },
      {
        Sid    = "EcsExecChannels"
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      },
      {
        Sid      = "ConfigParameterRead"
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters"]
        Resource = local.ecs_task_ssm_parameter_arns
      }
    ]
  })
}

# ── Worker Task Role ────────────────────────────────────────────────────────
resource "aws_iam_role" "ecs_task_worker" {
  name               = "${local.name_prefix}-ecs-task-worker-role"
  assume_role_policy = local.ecs_task_assume_role_policy

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ecs-task-worker-role" })
}

resource "aws_iam_role_policy" "ecs_task_worker" {
  name = "${local.name_prefix}-ecs-task-worker-access"
  role = aws_iam_role.ecs_task_worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListEvidenceAndReportBuckets"
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = [
          aws_s3_bucket.evidence.arn,
          aws_s3_bucket.report.arn
        ]
      },
      {
        # 증거: 분석용 읽기 전용. Worker는 증거를 수정/삭제하지 않는다.
        Sid      = "EvidenceObjectRead"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = ["${aws_s3_bucket.evidence.arn}/*"]
      },
      {
        # 리포트: PDF 생성(Put)·확인(Get). 삭제는 Backend(보관정책) 담당.
        Sid      = "ReportObjectReadWrite"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = ["${aws_s3_bucket.report.arn}/*"]
      },
      {
        Sid      = "EvidenceKmsUse"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey"]
        Resource = aws_kms_key.evidence.arn
      },
      {
        # Consumer: 메시지 수신·삭제만. SendMessage 불가.
        Sid    = "SqsConsume"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueUrl",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.analysis.arn
      },
      {
        # OCR·문장화(Bedrock) + 음성 전사(Transcribe) + 번역(Translate).
        Sid    = "AiPipeline"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "transcribe:StartTranscriptionJob",
          "transcribe:GetTranscriptionJob",
          "transcribe:DeleteTranscriptionJob",
          "transcribe:ListTranscriptionJobs",
          "transcribe:GetVocabulary",
          "transcribe:CreateVocabulary",
          "translate:TranslateText"
        ]
        Resource = "*"
      },
      {
        Sid    = "XRayWrite"
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
          "xray:GetSamplingStatisticSummaries"
        ]
        Resource = "*"
      },
      {
        Sid      = "AppSecretRead"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.app.arn
      },
      {
        Sid    = "EcsExecChannels"
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      },
      {
        Sid      = "ConfigParameterRead"
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters"]
        Resource = local.ecs_task_ssm_parameter_arns
      }
    ]
  })
}
