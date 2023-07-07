variable "owner" {
  type = string
  default = "newuser"
}

variable "group" {
  type = string
  default = "IT"
}

variable "ami_id" {
  type = string
  default = "ami-#################"
}

variable "instance_type" {
  type = string
  default = "t3.micro"
}

variable "ec2_name" {
  type = string
  default = "ec2-tst-001"
}

variable "subnet_id" {
  type = string
  default = "subnet-########"
}

variable "associate_public_ip_address" {
  type = bool
  default = false
}