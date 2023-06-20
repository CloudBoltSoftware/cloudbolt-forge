#!/usr/bin/env bash

# Installs python3.6 into the provisioned server.

yum install gcc openssl-devel bzip2-devel -y

vers=$(sudo cat /etc/centos-release | tr -dc '0-9.')

version=$(echo $vers | grep -Po "^...");

var=$(awk 'BEGIN{ print "'$version'"<"'7.0'" }')

yum update curl -y

if [ "$var" -eq 1 ];then
    curl -O -1 -L https://www.python.org/ftp/python/3.6.8/Python-3.6.8.tgz

else
    curl -O -L https://www.python.org/ftp/python/3.6.8/Python-3.6.8.tgz

fi

echo "Extracting pyhton..."
tar xzf Python-3.6.8.tgz


echo "Installing Python..."
cd Python-3.6.8

./configure --enable-optimizations
make altinstall

cd ..
echo "Removing downloaded source archive file from system..."
rm -rf Python-3.6.8.tgz

echo "Checking python version..."
python3.6 -V

echo "Done."
