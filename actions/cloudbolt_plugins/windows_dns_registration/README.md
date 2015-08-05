# Windows DNS Registration

## Purpose

The purpose of these scripts is to be able to pass IP and Hostname information from CloudBolt to a Windows DNS server to be registered as an A rec. The primary use case is situations where Windows DNS is used to server DNS for Linux hosts that are not using Windows DHCP to dynamically register DNS records.

## Prerequisites

1. A Windows VM running in a VMware vCenter instance running Windows DNS. (Note: This has been tested on Windows Server 2008 and later.)
2. vCenter credentials to get a remote execution context on the Windows DNS VM
3. Windows credentials with permission to execute dnscmd.exe locally on the Windows DNS host.
4. Two CloudBolt Plug-in Actions: register\_with\_win\_dns.py and deregister\_with\_win\_dns.py
5. A network that is setup to use static addressing and a CloudBolt resource pool that supplies a range of IPs.

## Installation

### Action Setup

1. In CloudBolt, go to Admin > Orchestration Actions, and click the "Provision Server" on the left of the UI.
2. Find the "Pre-Network Configuration" event and click "Add an Action" to add the DNS registration action.
3. Select "CloudBolt Plugin-in" from the "Choose Action Type" dialog.
4. Click "Add new cloudbolt plugin" in the "Create CloudBolt Plug-in Action" dialog.
5. In the "Add CloudBolt Plug-in Action" dialog:
 1. Enter the name "cbsw.RegisterWinDNS"
 2. Choose the groups or environments to which the action applies. Not selecting a group or environment means run the action for all.
 3. Click "Browse" and upload the script titled register\_with\_win\_dns.py.
6. Repeat the above process for deregistration of DNS info, this time selecting the "Delete Server" tab on the left, and adding the action to the "Post-Delete" event.

## Setup

### Connection Info for Windows DNS Server
1. Go to Admin > Database Browser and find/click the link for "Connection Info".
2. Click "Add connection Info"
3. For name, enter "WindowsDnsServer"
4. Enter the name of the VM running Windows DNS in the IP/Hostname field.
5. Leave "Port" blank
6. Set the username and password of the local Windows user to use to execute dnscmd.exe

### Connection Info for vCenter
1. Go to Admin > Database Browser and find/click the link for "Connection Info".
2. Click "Add connection Info"
3. For name, enter "vCenterServer"
4. Complete all fields with info for vCenter instance hosting the Windows DNS Server VM.

### IP Address Assignment
1. Make sure the applicable environment is using a network that requires static IP addresses.
2. Make sure the network is associated with a static IP address pool.


## Start Provisioning

Start with a Linux server. As it is provisioned, a message will be displayed in the job log indicating that CloudBolt is registering the new hostname and IP with Windows DNS.


