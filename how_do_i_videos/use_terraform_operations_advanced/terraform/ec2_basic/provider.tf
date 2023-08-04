terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.0"
    }
  }

  backend "s3" {
    bucket         = "cloudbolt-tfstates"
    key            = "terraform/terraform.tfstate"
    region         = "us-east-1"
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.region
}