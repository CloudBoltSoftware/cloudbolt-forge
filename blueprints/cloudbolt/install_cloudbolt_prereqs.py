#!/bin/sh
# this is a test
echo "Updating all RPMs presently installed"
yum update

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
