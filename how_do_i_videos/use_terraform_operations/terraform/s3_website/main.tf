terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.8.0"
    }
  }

  required_version = ">= 1.1.7"
}

# Configure the AWS Provider
provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "b1" {
  bucket = var.bucket_name
  tags = {
    Owner       = var.owner
    Group       = var.group
  }
}

resource "aws_s3_bucket_public_access_block" "b1" {
  bucket = aws_s3_bucket.b1.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_ownership_controls" "b1" {
  bucket = aws_s3_bucket.b1.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "b1" {
  depends_on = [
	aws_s3_bucket_public_access_block.b1,
	aws_s3_bucket_ownership_controls.b1,
  ]

  bucket = aws_s3_bucket.b1.id
  acl    = "public-read"
}

resource "aws_s3_bucket_policy" "policy" {
  depends_on = [ aws_s3_bucket_acl.b1 ]
  bucket = aws_s3_bucket.b1.id
  policy = templatefile("resources/policy.json", { bucket = var.bucket_name })
}

resource "aws_s3_bucket_website_configuration" "website" {
  bucket = aws_s3_bucket.b1.id
  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

resource "aws_s3_object" "index" {
  bucket       = aws_s3_bucket.b1.id
  key          = "index.html"
  source       = "resources/index.html"
  content_type = "text/html"
  etag = filemd5("resources/index.html")
}

resource "aws_s3_object" "error" {
  bucket       = aws_s3_bucket.b1.id
  key          = "error.html"
  source       = "resources/error.html"
  content_type = "text/html"
  etag = filemd5("resources/error.html")
}

resource "aws_s3_object" "cb_logo" {
  bucket       = aws_s3_bucket.b1.id
  key          = "cb_logo.png"
  source       = "resources/cb_logo.png"
  etag = filemd5("resources/cb_logo.png")
}
