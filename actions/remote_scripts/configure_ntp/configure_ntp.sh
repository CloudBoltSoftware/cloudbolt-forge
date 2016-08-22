#!/bin/sh -e

echo "Installing and configuring NTP"
 yum install -y ntp ntpdate ntp-doc
 chkconfig ntpd on

 echo "Synchronizing system time"
 ntpdate pool.ntp.org

