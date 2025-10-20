resource "google_project_iam_member" "project" {
  project = var.gcp_project_name
  role    = var.gcp_role_name
  member  = "user:${var.gcp_user_name}"
}
