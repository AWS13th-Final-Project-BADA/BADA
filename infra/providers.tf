terraform {
  required_version = ">= 1.6.0"

  backend "s3" {
    bucket       = "bada-tfstate-165749212250-ap-northeast-2"
    key          = "bada/dev/terraform.tfstate"
    region       = "ap-northeast-2"
    use_lockfile = true
    encrypt      = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # 비용 할당 태그 catch-all(B-4): 모든 리소스에 기본 태그를 자동 부착한다.
  # 개별 리소스의 merge(local.common_tags, ...)와 키/값이 동일하므로 기존
  # 리소스에는 plan 변화가 없고, 태그가 누락된 리소스만 보강된다.
  # Cost Explorer/Billing에서 Project·Environment 태그로 비용 분해 가능.
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
