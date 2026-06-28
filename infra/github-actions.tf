data "aws_caller_identity" "current" {}

data "aws_iam_openid_connect_provider" "github_actions" {
  arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
}

locals {
  github_repository_slug = "${var.github_owner}/${var.github_repository}"
}

# ─── Terraform Plan in PR (읽기 전용) ────────────────────────────────────────
# PR(pull_request)에서 terraform plan을 실행하기 위한 읽기 전용 역할.
# deploy 역할(develop 한정·쓰기 권한)과 분리한다. apply 권한은 부여하지 않는다.
resource "aws_iam_role" "github_actions_plan" {
  name = "${local.name_prefix}-github-actions-plan-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = data.aws_iam_openid_connect_provider.github_actions.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          # PR 이벤트(어느 feature 브랜치든)에서만 assume 가능. push/deploy ref는 제외.
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${local.github_repository_slug}:pull_request"
          }
        }
      }
    ]
  })

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-github-actions-plan-role" })
}

# terraform plan은 전체 리소스 refresh를 위해 광범위한 읽기가 필요하다.
# AWS 관리형 ReadOnlyAccess로 부여하고, 쓰기/apply 권한은 일절 주지 않는다.
resource "aws_iam_role_policy_attachment" "github_actions_plan_readonly" {
  role       = aws_iam_role.github_actions_plan.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

resource "aws_iam_role_policy" "github_actions_plan_secret_read" {
  name = "${local.name_prefix}-github-actions-plan-secret-read"
  role = aws_iam_role.github_actions_plan.id

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
      }
    ]
  })
}

resource "aws_iam_role" "github_actions_deploy" {
  name = "${local.name_prefix}-github-actions-deploy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = data.aws_iam_openid_connect_provider.github_actions.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
            "token.actions.githubusercontent.com:sub" = "repo:${local.github_repository_slug}:ref:refs/heads/${var.github_deploy_branch}"
          }
        }
      }
    ]
  })

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-github-actions-deploy-role" })
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name = "${local.name_prefix}-github-actions-deploy-policy"
  role = aws_iam_role.github_actions_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EcrLogin"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Sid    = "AppEcrPush"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:CompleteLayerUpload",
          "ecr:DescribeImages",
          "ecr:DescribeRepositories",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart"
        ]
        Resource = concat(
          [
            aws_ecr_repository.backend.arn,
            aws_ecr_repository.worker.arn
          ],
          var.frontend_enabled ? [aws_ecr_repository.frontend[0].arn] : []
        )
      },
      {
        Sid    = "BackendEcsDeploy"
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:UpdateService"
        ]
        Resource = "*"
      },
      {
        Sid    = "AlbHealthCheckDiscovery"
        Effect = "Allow"
        Action = [
          "elasticloadbalancing:DescribeLoadBalancers"
        ]
        Resource = "*"
      },
      {
        Sid    = "PassEcsTaskRoles"
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.ecs_task.arn
        ]
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "ecs-tasks.amazonaws.com"
          }
        }
      }
    ]
  })
}
