output "storage_account_name" {
  value = azurerm_storage_account.account.name
}

output "storage_container_name" {
  value = azurerm_storage_container.storage_container.name
}

output "web_endpoint" {
  value = azurerm_storage_account.account.primary_web_endpoint
}

output "connection_string" {
  value = azurerm_storage_account.account.primary_connection_string
  sensitive = true
}