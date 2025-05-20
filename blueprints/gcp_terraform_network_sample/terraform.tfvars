db_authorized_networks = [
  {
    name  = var.gcp_authorized_networks_name
    cidr = var.gcp_authorized_networks_cidr
  },
]
gcp_project_id = "customer-success-gcp-project"
# gcp_project_name = "customer-success-gcp-project"
gcp_region = "us-east1"
gcp_db_instance_name = "customer-success-db-instance"
gcp_database_version = "POSTGRES_15"
gcp_tier = "db-f1-micro"
gcp_availability_type = "ZONAL"
gcp_db_name = "oparlak_test_db"
gcp_db_user = "oparlak_db_user"
# gcp_authorized_networks_name = "customer-success-network"
# gcp_authorized_networks_cidr = "10.10.10.1/24"
