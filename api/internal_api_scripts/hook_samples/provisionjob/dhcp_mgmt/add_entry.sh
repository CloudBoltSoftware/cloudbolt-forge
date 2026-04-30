#!/bin/sh

if [ $# != 3 ]; then
  echo "usage: add_entry <host_label> <mac> <ip>"
  exit 1
fi

host_label=$1
mac=$2
ip=$3

grep "^host ${host_label}" /etc/dhcp/dhcpd.conf > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "${host_label} already exists in /etc/dhcp/dhcpd.conf, removing and re-adding."
  /etc/dhcp/rem_entry $1
fi

cat >> /etc/dhcp/dhcpd.conf <<EOF
host ${host_label} {
  hardware ethernet ${mac};
  fixed-address ${ip};
} # end ${host_label}
EOF

/etc/init.d/isc-dhcp-server force-reload
