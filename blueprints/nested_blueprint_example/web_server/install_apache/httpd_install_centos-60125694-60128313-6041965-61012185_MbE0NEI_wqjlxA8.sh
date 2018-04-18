#!/bin/bash
#
# Install apache & git
yum install httpd git -y

# Start service
service httpd start

# Disable selinux
setenforce 0

# Open up incoming traffic on TCP ports 80 & 443
iptables -A INPUT -p tcp -m tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp -m tcp --dport 443 -j ACCEPT
/etc/init.d/iptables save