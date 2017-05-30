#!/bin/bash

# Used as part of the CentOS Development Environment Blueprint
# Adapted from https://gist.github.com/rothgar/cecfbd74597cc35a6018

# Install dependencies
yum install gcc kernel-devel make ncurses-devel -y

# DOWNLOAD SOURCES FOR LIBEVENT AND MAKE AND INSTALL
curl -OL https://github.com/libevent/libevent/releases/download/release-2.1.8-stable/libevent-2.1.8-stable.tar.gz
tar -xvzf libevent-2.1.8-stable.tar.gz
cd libevent-2.1.8-stable
./configure --prefix=/usr/local
make
make install

# DOWNLOAD SOURCES FOR TMUX AND MAKE AND INSTALL
curl -OL https://github.com/tmux/tmux/releases/download/2.4/tmux-2.4.tar.gz
tar -xvzf tmux-2.4.tar.gz
cd tmux-2.4
LDFLAGS="-L/usr/local/lib -Wl,-rpath=/usr/local/lib" ./configure --prefix=/usr/local
make
make install
