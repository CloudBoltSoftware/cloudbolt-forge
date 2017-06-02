#!/bin/sh

echo "Removing any old CB installers, in case they exist"
rm -f cloudbolt_installer_*.tgz

echo "Opening up incoming traffic on TCP ports 80 & 443"
iptables -I INPUT 2 -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT
iptables -I INPUT 2 -m state --state NEW -m tcp -p tcp --dport 443 -j ACCEPT
service iptables save
service iptables restart

echo "Downloading CloudBolt"
wget --no-verbose http://downloads.cloudbolt.io/cloudbolt-installer-latest.tgz

echo "Extracting CloudBolt Archive"
tar xfz cloudbolt_installer_*.tgz
cd cloudbolt_installer*

echo "Installing CloudBolt"
./install_cloudbolt.sh force