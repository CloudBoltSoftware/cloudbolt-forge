resource "aws_instance" "server" {
    ami = var.ami_id
    instance_type = var.instance_type
    subnet_id = var.subnet_id
    associate_public_ip_address = var.associate_public_ip_address

    tags = {
        Name = var.ec2_name
        group = var.group
        owner = var.owner
    }
}

output "instance_id" {
  value = aws_instance.server.id
}

output "private_ip" {
    value = aws_instance.server.private_ip
}

output "public_ip" {
    value = aws_instance.server.public_ip
}

output "public_dns" {
    value = aws_instance.server.public_dns
}