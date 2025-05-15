terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">=6.34.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_name
  credentials = file("var./var/opt/cloudbolt/proserv/gcp_creds")
}