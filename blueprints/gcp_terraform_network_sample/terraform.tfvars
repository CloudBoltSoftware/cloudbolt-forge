authorized_networks = [
  {
    name  = var.gcp_authorized_networks_name
    value = var.gcp_authorized_networks_cidr
  },
  {
    name  = "home"
    value = "198.51.100.0/24"
  }
]
