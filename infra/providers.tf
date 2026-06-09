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
  }
}

provider "aws" {
  region = var.aws_region
}
