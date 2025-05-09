resource "google_project_iam_member" "project" {
  project = var.gcp_project_name
  role    = var.gcp_role_name
  member  = "user:${var.gcp_user_name}"
}
resource "null_resource" "write_creds" {
  provisioner "local-exec" {
    command = <<EOT
echo '${var.web_client_json}' > ./gcp_creds.json
EOT
  }
}
