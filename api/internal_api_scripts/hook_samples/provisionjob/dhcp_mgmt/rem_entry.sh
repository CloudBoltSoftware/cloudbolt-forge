#!/bin/sh

if [ $# != 1 ]; then
  echo "usage: rem_entry <host_label>"
  exit 1
fi

host_label=$1

grep "^host ${host_label}" /etc/dhcp/dhcpd.conf > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "${host_label} doesn't exist in /etc/dhcp/dhcpd.conf"
  exit 0
fi

perl -i -pe "BEGIN{undef $/;} s/^host ${host_label}.*} # end ${host_label}\n//smg" /etc/dhcp/dhcpd.conf

/etc/init.d/isc-dhcp-server force-reload
