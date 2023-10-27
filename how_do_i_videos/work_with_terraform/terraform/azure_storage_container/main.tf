data "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
}

resource "azurerm_storage_account" "account" {
  name                     = var.storage_account_name
  resource_group_name      = data.azurerm_resource_group.rg.name
  location                 = data.azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = var.account_replication_type

  tags = {
    cost_center = var.cost_center
    owner       = var.owner
    group       = var.group
  }
}

resource "azurerm_storage_container" "storage_container" {
  name                  = var.storage_container_name
  storage_account_name  = azurerm_storage_account.account.name
  container_access_type = "private"
}
