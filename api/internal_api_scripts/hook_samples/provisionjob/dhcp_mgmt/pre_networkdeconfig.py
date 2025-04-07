# pre_networkdeconfig.py decomjob hook called when a VM is decommissioned
# implements the ''disable dns and dhcp'' features required to set the IP address on Xen VMs

import sys          # reads command-line args
import httplib      # basic HTTP library for HTTPS connections
import urllib       # used for url-encoding during login request
import json         # converts between JSON and python objects
import re           # needed for split function

from utilities.run_command import run_command as global_run_command


def disable_dns(svc_ip, svc_authuser, vm_name, dns_ip, dns_domain, ip):
    '''
#!/bin/sh

if [ $# != 3 ]; then
  echo "usage: rem_entry <hostname> <domain> <ip>"
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
  perl -i -pe "BEGIN{undef $/;} s/^${hostname}\sIN A\s${ip}\n//smg" \
    /var/named/data/${domain}.fwd
fi

IFS=. read ip1 ip2 ip3 ip4 <<< "${ip}"
unset IFS

if [ ! -f /var/named/data/${domain}.rev ]; then
  echo "The domain: ${domain}.rev reverse zone file does not exist."
  exit 1
else
  grep "^${ip4}" /var/named/data/${domain}.rev > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    perl -i -pe "BEGIN{undef $/;} s/^${ip4}\sIN PTR\s${hostname}\.${domain}\.\n//smg" \
      /var/named/data/${domain}.rev
  else
    echo "The hostname: ${hostname} was not found in the ${domain}.rev reverse zone file."
    exit 0
  fi
fi

/etc/init.d/named reload
    '''
    command = "su - apache -c 'ssh %s@%s sudo /var/named/rem_entry %s %s %s'" % \
              (svc_authuser, svc_ip, vm_name, dns_domain, ip)

    return global_run_command(command)


def disable_dhcp(dhcp_server, dhcp_authuser, vm_name, mac, ip):
    '''
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

perl -i -pe "BEGIN{undef $/;} s/^host ${host_label}.*} # end ${host_label}\n//smg" \
   /etc/dhcp/dhcpd.conf

/etc/init.d/isc-dhcp-server force-reload
    '''
    command = "su - apache -c 'ssh %s@%s sudo /etc/dhcp/rem_entry %s'" % \
              (dhcp_authuser, dhcp_server, vm_name)

    return global_run_command(command)


def disable_network_services(server, logger):
  logger.info("in disable_network_services hook, for server: %s" % server)

	handler = server.environment.resource_handler.cast()
	res_name = server.get_vm_name()

	logger.info("server name: %s" % res_name)
	logger.info("nvp controller: %s" % server.nvpcontroller)
	logger.info("NIC 0: %s" % server.sc_nic_0)
	logger.info("NIC 1: %s" % server.sc_nic_1)

	handler.resource_technology.init(handler.ip, handler.port,
                                  handler.serviceaccount, handler.servicepasswd)

	if server.sc_nic_0 is not None:
		logger.info("in detach_vif_from_server hook, server.sc_nic_0: about to get MAC")
		mac = handler.resource_technology.work_class.get_nic_mac(res_name, "Network adapter 1")
		if mac is None:
			mac = handler.resource_technology.work_class.get_nic_mac_device(res_name, "0")
		logger.info("sc_nic_0 mac: %s" % mac)

		nic = server.nics.all()[0]

		logger.info("got nic")

		dns_ns1 = nic.network.dns1
		dns_ns2 = nic.network.dns2

		logger.info("dns_ns1: %s, dns_ns2: %s" % (dns_ns1, dns_ns2))

		cfs = nic.network.custom_field_values.all()

		logger.info("cfs: %s" % cfs)

		try:
			cf_dns_server = cfs.filter(field__name__contains='dns_server')[0]
			cf_dns_authuser = cfs.filter(field__name__contains='dns_authuser')[0]
			cf_dns_domain = cfs.filter(field__name__contains='dns_domain')[0]
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

		logger.info("calling disable_dns(%s, %s, %s, %s, %s, %s)" %
                    (dns_server, dns_authuser, res_name, dns_ns1, dns_domain, nic.ip))

		disable_dns(dns_server, dns_authuser, res_name, dns_ns1, dns_domain, nic.ip)

		if "Xen" in handler.name:
			logger.info("in if Xen codeblock")
			try:
				cf_dhcp_server = cfs.filter(field__name__contains='dhcp_server')[0]
				cf_dhcp_authuser = cfs.filter(field__name__contains='dhcp_authuser')[0]
			except:
				pass

			if cf_dhcp_server:
				dhcp_server = cf_dhcp_server.value
			else:
				raise Exception("CF dhcp_server does not exist.")

			if cf_dhcp_authuser:
				dhcp_authuser = cf_dhcp_authuser.value
			else:
				raise Exception("CF dhcp_authuser does not exist.")

			logger.info("calling disable_dhcp(%s, %s, %s, %s, %s)" %
                            (dhcp_server, dhcp_authuser, res_name + "-0", mac, nic.ip))

			disable_dhcp(dhcp_server, dhcp_authuser, res_name + "-0", mac, nic.ip)

	if server.sc_nic_1 is not None:
		mac = handler.resource_technology.work_class.get_nic_mac(res_name, "Network adapter 1")
		if mac is None:
			mac = handler.resource_technology.work_class.get_nic_mac_device(res_name, "1")
		logger.info("sc_nic_1 mac: %s" % mac)

		nic = server.nics.all()[1]

		dns_ns1 = nic.network.dns1
		dns_ns2 = nic.network.dns2

		cfs = nic.network.custom_field_values.all()

		try:
			cf_dns_server = cfs.filter(field__name__contains='dns_server')[0]
			cf_dns_authuser = cfs.filter(field__name__contains='dns_authuser')[0]
			cf_dns_domain = cfs.filter(field__name__contains='dns_domain')[0]
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

		logger.info("calling disable_dns(%s, %s, %s, %s, %s, %s)" %
                    (dns_server, dns_authuser, res_name, dns_ns1, dns_domain, nic.ip))

		disable_dns(dns_server, dns_authuser, res_name, dns_ns1, dns_domain, nic.ip)

		if "Xen" in handler.name:
			try:
				cf_dhcp_server = cfs.filter(field__name__contains='dhcp_server')[0]
				cf_dhcp_authuser = cfs.filter(field__name__contains='dhcp_authuser')[0]
			except:
				pass

			if cf_dhcp_server:
				dhcp_server = cf_dhcp_server.value
			else:
				raise Exception("CF dhcp_server does not exist.")

			if cf_dhcp_authuser:
				dhcp_authuser = cf_dhcp_authuser.value
			else:
				raise Exception("CF dhcp_authuser does not exist.")

			logger.info("calling disable_dhcp(%s, %s, %s, %s, %s)" %
                            (dhcp_server, dhcp_authuser, res_name + "-1", mac, nic.ip))

			disable_dhcp(dhcp_server, dhcp_authuser, res_name + "-1", mac, nic.ip)

      return "","",""
