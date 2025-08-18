# post_networkconfig.py provisionjob hook called just after the network interfaces have been enabled on the VM
# implements the ''enable dns and dhcp'' features required to set the IP address on Xen VMs

# requires the following custom fields (CFs) to be set:
#
#  cf_dns_server = IP Address of DNS server
#  cf_dns_authuser = user authorized to make changes to the DNS service (via passwordless ssh to the DNS host from the CloudBolt server)
#  cf_dns_domain = DNS domainname
#  cf_dhcp_server = IP Address of the DHCP server (running on an Ubuntu linux instance)
#  cf_dhcp_authuser = user authorized to make changes to the DHCP service (via passwordless ssh to the DHCP host from the CloudBolt server)
#

# on VMware and Xen VMs DNS configuration is always performed, on Xen DHCP
# configuration is also performed

import sys  # reads command-line args
import httplib  # basic HTTP library for HTTPS connections
import urllib  # used for url-encoding during login request
import json  # converts between JSON and python objects
import re  # needed for split function
import time

from utilities.run_command import run_command as global_run_command


def enable_dns(svc_ip, svc_authuser, vm_name, dns_ip, dns_domain, ip):
    """
#!/bin/sh

if [ $# != 3 ]; then
  echo "usage: add_entry <hostname> <domain> <ip>"
  exit 1
fi

hostname=$1
domain=$2
ip=$3

if [ ! -f /var/named/data/${domain}.fwd ]; then
  echo "The domain: ${domain}.fwd forward zone file does not exist."
  exit 1
fi

grep "^${hostname}" /var/named/data/${domain}.fwd > /dev/null 2>&1
if [ $? -eq 0 ]; then
  #echo "A host with the name ${hostname} already exists in the ${domain}.fwd file."
  #exit 1
  /var/named/rem_entry $1 $2 $3
fi

cat >> /var/named/data/${domain}.fwd <<EOF
${hostname}     IN A    ${ip}
EOF

if [ ! -f /var/named/data/${domain}.rev ]; then
  echo "The domain: ${domain}.rev reverse zone file does not exist."
  exit 1
fi

IFS=. read ip1 ip2 ip3 ip4 <<< "${ip}"
unset IFS

cat >> /var/named/data/${domain}.rev <<EOF
$ip4    IN PTR ${hostname}.${domain}.
EOF

/etc/init.d/named reload
    """
    command = "su - apache -c 'ssh %s@%s sudo /var/named/add_entry %s %s %s'" % (
        svc_authuser,
        svc_ip,
        vm_name,
        dns_domain,
        ip,
    )

    return global_run_command(command)


def enable_dhcp(dhcp_server, dhcp_authuser, vm_name, mac, ip, netmask, gateway):
    """
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
  echo "${host_label} already exists in /etc/dhcp/dhcpd.conf."
  exit 1
fi

cat >> /etc/dhcp/dhcpd.conf <<EOF
host ${host_label} {
  hardware ethernet ${mac};
  fixed-address ${ip};
} # end ${host_label}
EOF

/etc/init.d/isc-dhcp-server force-reload
    """
    command = "su - apache -c 'ssh %s@%s sudo /etc/dhcp/add_entry %s %s %s'" % (
        dhcp_authuser,
        dhcp_server,
        vm_name,
        mac,
        ip,
    )

    return global_run_command(command)


def run(job, logger):
    logger.info("in post_networkconfig hook, %s job.id=%s" % (__name__, job.id))

    # try:
    server = job.server_set.all()[0]
    handler = server.environment.resource_handler.cast()
    res_name = handler.get_vm_name(server)

    logger.info("server name: %s" % res_name)
    logger.info("NIC 0: %s" % server.sc_nic_0)
    logger.info("NIC 1: %s" % server.sc_nic_1)

    # Configure DNS based on the first network interface
    nic = server.nics.all()[0]

    dns_ns1 = nic.network.dns1
    dns_ns2 = nic.network.dns2
    cfs = nic.network.custom_field_values.all()

    cf_dns_server = None
    cf_dns_authuser = None
    cf_dns_domain = None

    try:
        cf_dns_server = cfs.filter(field__name__contains="dns_server")[0]
        cf_dns_authuser = cfs.filter(field__name__contains="dns_authuser")[0]
        cf_dns_domain = cfs.filter(field__name__contains="dns_domain")[0]
    except:
        pass

    if cf_dns_server:
        dns_server = cf_dns_server.value
    else:
        logger.info("CF dns_server: missing, please create a CF for dns_server")

    if cf_dns_authuser:
        dns_authuser = cf_dns_authuser.value
    else:
        logger.info("CF dns_authuser: missing, please create a CF for dns_authuser")

    if cf_dns_domain:
        dns_domain = cf_dns_domain.value
    else:
        logger.info("CF dns_domain: missing, please create a CF for dns_domain")

    enable_dns(dns_server, dns_authuser, res_name, dns_ns1, dns_domain, nic.ip)

    logger.info("\nServer is: %s" % (res_name))
    handler.resource_technology.init(
        handler.ip, handler.port, handler.serviceaccount, handler.servicepasswd
    )

    if server.sc_nic_0 is not None:
        mac = handler.resource_technology.work_class.get_nic_mac(
            res_name, "Network adapter 1"
        )
        if mac is None:
            mac = handler.resource_technology.work_class.get_nic_mac_device(
                res_name, "0"
            )
        logger.info("sc_nic_0 mac: %s" % mac)

        if "Xen" in handler.name:
            # for Xen we need DHCP to setup an IP address reservation
            nic = server.nics.all()[0]
            cfs = nic.network.custom_field_values.all()

            cf_dhcp_server = None
            cf_dhcp_authuser = None

            try:
                cf_dhcp_server = cfs.filter(field__name__contains="dhcp_server")[0]
                cf_dhcp_authuser = cfs.filter(field__name__contains="dhcp_authuser")[0]
            except:
                pass

            dhcp_server = None
            if cf_dhcp_server:
                dhcp_server = cf_dhcp_server.value
            else:
                raise Exception("CF dhcp_server does not exist.")

            dhcp_authuser = None
            if cf_dhcp_authuser:
                dhcp_authuser = cf_dhcp_authuser.value
            else:
                raise Exception("CF dhcp_authuser does not exist.")

            enable_dhcp(
                dhcp_server,
                dhcp_authuser,
                res_name + "-0",
                mac,
                nic.ip,
                nic.network.netmask,
                nic.network.gateway,
            )

    if server.sc_nic_1 is not None:
        mac = handler.resource_technology.work_class.get_nic_mac(
            res_name, "Network adapter 2"
        )
        if mac is None:
            mac = handler.resource_technology.work_class.get_nic_mac_device(
                res_name, "1"
            )
        logger.info("sc_nic_1 mac: %s" % mac)

        if "Xen" in handler.name:
            # for Xen we need DHCP to setup an IP address reservation
            nic = server.nics.all()[1]
            cfs = nic.network.custom_field_values.all()

            cf_dhcp_server = None
            cf_dhcp_authuser = None

            try:
                cf_dhcp_server = cfs.filter(field__name__contains="dhcp_server")[0]
                cf_dhcp_authuser = cfs.filter(field__name__contains="dhcp_authuser")[0]
            except:
                pass

            dhcp_server = None
            if cf_dhcp_server:
                dhcp_server = cf_dhcp_server.value
            else:
                raise Exception("CF dhcp_server does not exist.")

            dhcp_authuser = None
            if cf_dhcp_authuser:
                dhcp_authuser = cf_dhcp_authuser.value
            else:
                raise Exception("CF dhcp_authuser does not exist.")

            enable_dhcp(
                dhcp_server,
                dhcp_authuser,
                res_name + "-1",
                mac,
                nic.ip,
                nic.network.netmask,
                nic.network.gateway,
            )

    return "", "", ""
