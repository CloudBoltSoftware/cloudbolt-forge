#!/bin/sh

export PATH=/usr/local/bin:${PATH}
echo -n "Path is now "
echo ${PATH}

echo "Removing any old CB installers, in case they exist"
rm -f cloudbolt-installer-*.tgz*

echo "Opening up incoming traffic on TCP ports 80 & 443"
iptables -I INPUT 2 -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT
iptables -I INPUT 2 -m state --state NEW -m tcp -p tcp --dport 443 -j ACCEPT
service iptables save
service iptables restart

echo "Downloading CloudBolt"
wget --no-verbose http://downloads.cloudbolt.io/cloudbolt-installer-latest.tgz

echo "Extracting CloudBolt Archive"
tar xfz cloudbolt-installer-*.tgz
cd cloudbolt_installer*

echo "Installing MySQL server"
OLD=`pwd`
cd 02-mysql57-upgrade
yum -y install ./mysql*-community-release*rpm
cd server_packages
yum -y install ./mysql*server*rpm
cd ${OLD}

echo "Installing CloudBolt"
./install_cloudbolt.sh force

# vim: set ts=2 et tw=78 ff=unix ft=sh:
