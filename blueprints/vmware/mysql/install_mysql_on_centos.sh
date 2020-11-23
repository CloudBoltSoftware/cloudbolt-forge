#!/usr/bin/env bash

vers=$(sudo cat /etc/centos-release | tr -dc '0-9.')

version=$(echo $vers | grep -Po "^...");

var=$(awk 'BEGIN{ print "'$version'"<"'7.0'" }')

cd /root

if [ "$var" -eq 1 ];then
    yum update curl -y

    curl -O -1 -L https://dev.mysql.com/get/mysql80-community-release-el6-3.noarch.rpm
    yum localinstall mysql80-community-release-el6-3.noarch.rpm -y
    yum install mysql-community-server -y
    service mysqld start

else
    yum update curl -y

    curl -O -L https://dev.mysql.com/get/mysql80-community-release-el7-3.noarch.rpm
    yum localinstall mysql80-community-release-el7-3.noarch.rpm -y
    yum install mysql-community-server -y
    service mysqld start

fi

# Open up incoming traffic on TCP ports 3306
iptables -A INPUT -p tcp -m tcp --dport 3306 -j ACCEPT

/etc/init.d/iptables save

echo "DONE!!"
