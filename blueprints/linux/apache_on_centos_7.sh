#!/bin/bash
#
# Install apache & git
yum install httpd git -y

# Start service
systemctl restart httpd.service

# Disable selinux
setenforce 0

# Open up incoming traffic on TCP ports 80 & 443
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp

firewall-cmd --reload