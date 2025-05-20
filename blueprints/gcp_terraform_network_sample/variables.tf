variable "gcp_project_name" {
  type        = string
  description = "GCP Project name"
}

variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP Region"
  type        = string
}

variable "gcp_db_instance_name" {
  description = "Name of the Cloud SQL instance"
  type        = string
}

variable "gcp_database_version" {
  description = "PostgreSQL version"
  type        = string
}

variable "gcp_tier" {
  description = "Machine type tier (e.g. db-f1-micro, db-custom-1-3840)"
  type        = string
}

variable "gcp_availability_type" {
  description = "Availability type: ZONAL or REGIONAL"
  type        = string
  default     = "ZONAL"
}

variable "db_authorized_networks" {
  description = "List of authorized networks with name and CIDR"
  type = list(object({
    name  = string
    value = string
  }))
}


variable "gcp_db_name" {
  description = "Name of the database to create"
  type        = string
}

variable "gcp_db_user" {
  description = "Database user name"
  type        = string
}

variable "gcp_db_password" {
  description = "Database user password"
  type        = string
  sensitive   = true
}
