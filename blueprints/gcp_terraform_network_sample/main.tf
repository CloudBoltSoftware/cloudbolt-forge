resource "google_sql_database_instance" "default" {
  name             = var.gcp_db_instance_name
  database_version = var.gcp_database_version
  region           = var.gcp_region
  project          = var.gcp_project_name

  settings {
    tier              = var.gcp_tier
    availability_type = var.gcp_availability_type

    ip_configuration {
      ipv4_enabled = true
      dynamic "db_authorized_networks" {
        for_each = authorized_networks
        content {
          name  = authorized_networks.value.name        #Cidr name
          value = authorized_networks.value.cidr        #Cidr value  
        }
      }
    }
    backup_configuration {
      enabled = true
    }
  }
}

resource "google_sql_user" "postgres_user" {
  name     = var.gcp_db_user
  instance = google_sql_database_instance.postgres.name
  password = var.gcp_db_password
}

resource "google_sql_database" "default_db" {
  name     = var.gcp_db_name
  instance = google_sql_database_instance.postgres.name
}
