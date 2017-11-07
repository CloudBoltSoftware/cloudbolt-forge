#!/bin/sh

if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root, attempting to gain privileges" 1>&2
   retval=`sudo -s basename "$0"`
   exit ${retval}
fi

echo "Making sure you run a supported OS"
LOCALVER=`awk '{ print $3 }' /etc/centos-release | cut -d\. -f1`
OSVERSION=${LOCALVER:-unknown}

if [ ${OSVERSION} != "6" ]; then
  echo "Nope. You seem to be running version $OSVERSION of CentOS. Please install CloudBolt on version 6"
  exit 1
fi

echo "Updating all RPMs presently installed"
yum update -y

echo "Installing additional RPMs needed by CloudBolt"
yum install -y \
    automake \
    bzip2-devel \
    cairo-devel \
    crontabs \
    dmidecode \
    e2fsprogs-devel \
    freetype \
    freetype-devel \
    gcc \
    gcc-c++ \
    httpd \
    libart_lgpl-devel \
    libevent \
    libpng-devel \
    libuuid-devel \
    libxml2-devel \
    libxslt \
    libxslt-devel \
    make \
    memcached \
    mod_ssl \
    ncurses \
    ncurses-devel \
    openldap \
    openldap-devel \
    openssl-devel \
    pango \
    pango-devel \
    perl \
    perl-CPAN \
    perl-Digest-SHA \
    perl-ExtUtils-MakeMaker \
    python-imaging \
    readline \
    readline-devel \
    sqlite-devel \
    screen \
    unzip \
    uuid \
    wget
    
# Disable SElinux and schedule shutdown in 1 minute. Clean exit afterwards.
sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/sysconfig/selinux
sed -i 's/SELINUX=permissive/SELINUX=disabled/' /etc/sysconfig/selinux
/sbin/shutdown -r +1

# vim: set ts=2 et tw=78 ff=unix ft=sh:
