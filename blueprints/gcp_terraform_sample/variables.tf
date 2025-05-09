variable "gcp_project_name" {
  type        = string
  description = "GCP Project name"
}
variable "gcp_role_name" {
  type        = string
  description = "Permission name, type roles/REQUESTEDROLE"
}
variable "gcp_user_name" {
  type        = string
  description = "User email address"
}
variable "gcp_credentials_json" {
  description = "GCP credentials JSON string"
  type        = string
}