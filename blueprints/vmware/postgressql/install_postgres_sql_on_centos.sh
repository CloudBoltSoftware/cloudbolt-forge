#!/usr/bin/env bash

echo "Installing PostgreSQL..."
yum install postgresql-server postgresql-contrib -y

echo " initializing the database..."
service postgresql initdb

echo "starting the database..."
service postgresql start

echo "Enabling Postgressql start on every system reboot.."
vers=$(sudo cat /etc/centos-release | tr -dc '0-9.')

version=$(echo $vers | grep -Po "^...");

var=$(awk 'BEGIN{ print "'$version'"<"'7.0'" }')
if [ "$var" -eq 1 ];then
    chkconfig --add postgresql
else
    systemctl enable postgresql
fi

echo "Opening up incoming traffic on TCP ports 5432"

# Open up incoming traffic on TCP ports 5432
iptables -A INPUT -p tcp -m tcp --dport 5432 -j ACCEPT

/etc/init.d/iptables save

echo "DONE!"
