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
  credentials = file("./gcp_creds.json")

  # credentials = jsondecode(var.gcp_credentials_json)
}

# Use below provider if testing locally 
# provider "google" {
#   credentials = "acs-eo-is-shared-001-ecb2095cea5_override.tf.json"
# }
