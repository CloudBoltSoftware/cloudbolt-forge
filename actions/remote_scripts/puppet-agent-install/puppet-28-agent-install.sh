#!/bin/bash
yum install -y puppet

PUPPET_CONF=$(cat <<'END_OF_CONFIG'
[main]
    logdir = /var/log/puppet
    rundir = /var/run/puppet
    ssldir = $vardir/ssl
    server = puppetee28.lab.iad.cloudboltsw.com
    pluginsync = true
[agent]
    classfile = $vardir/classes.txt
    localconfig = $vardir/localconfig
    runinterval = 5m
END_OF_CONFIG
)

echo "$PUPPET_CONF" > /etc/puppet/puppet.conf

sleep 10
service puppet start

