variable "resource_group_name" {
  type = string
  default = "mb-testing"
}

variable "storage_account_name" {
  type = string
  default = "mbcbtestaccount1"
}

variable "storage_container_name" {
  type = string
  default = "mbcbtestcontainer1"
}

variable "account_replication_type" {
  type = string
  default = "LRS"
}

variable "cost_center" {
  type = string
  default = "8943756"
}

variable "owner" {
  type = string
  default = "mbombard@cloudbolt.io"
}

variable "group" {
  type = string
  default = "IT"
}