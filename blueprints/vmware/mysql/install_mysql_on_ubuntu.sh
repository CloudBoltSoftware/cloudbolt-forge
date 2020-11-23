#!/usr/bin/env bash

apt-get install mysql-server

#Allow remote Access
sudo ufw allow mysql

#Start the MySQL service
systemctl start mysql

#Launch at reboot
systemctl enable mysql
