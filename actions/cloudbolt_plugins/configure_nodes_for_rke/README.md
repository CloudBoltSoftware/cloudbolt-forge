# Rancher Kubernetes Engine Plugin

> !! CENTOS ONLY !! This plugin only works for CentOS servers and requires the `yum` package manager.

This plugin builds and deploys a vanilla Kubernetes cluster onto the servers provisioned in a Blueprint.
Each server is assigned one or more roles from: Kube API server, Kube worker, and etcd server.

## Usage

Create a Blueprint with this plugin as the step _after_ one or more servers have been provisioned.

After the Blueprint order completes, you can grab the Kubernetes cluster information and create a CloudBolt Container Orchestrator.

## Pre-requisites

A few binaries must be installed on the CloudBolt Jobengine servers for this plugin to run successfully.
These do not have system packages, so the binaries need to be downloaded and placed on the system manually.

### RKE

You will need to manually install `rke` onto your CloudBolt server.
This plugin assumes an `rke` executable exists in the CloudBolt server `root` user's path;
e.g., at `/usr/local/bin/rke`.
See https://github.com/rancher/rke/releases for instructions.

### kubectl

You should also install `kubectl` on the CloudBolt server, similar to how you installed `rke`.
See https://kubernetes.io/docs/tasks/tools/install-kubectl/ for instructions.

## System/Hypervisor/Cloud-provider Requirements

### Network Security Groups

The Plugin following ports required for Kubernetes services to run and communicate between servers:

* 80/tcp
* 443/tcp
* 10250/tcp
* 2379/tcp
* 2380/tcp
* 6443/tcp
* 8285/udp
* 8472/udp

It also requires SSH from the CloudBolt server to the newly created servers, so you should expose these ports too:

* 22/tcp

If you are running in the cloud, add the above ports to a security group allowing incoming traffic from IP ranges including the CloudBolt server and the newly provisioned servers.

### Node size

Note that Kubernetes clusters, especially those with only a few nodes, have a lot of overhead in CPU and memory,
so using smaller node sizes may be slow and error/timeout-prone.

We suggest using at least "medium" size nodes with this Plugin to avoid that overhead performance cost.

## Deployment Specifics

This plugin will provision one Kubernetes cluster per Catalog Item order.

Each cluster is unique to the Resource and the clusters have files on disk which can be inspected for troubleshooting purposes.
For example, a Resource with ID 101 can be found on the CloudBolt host at `/var/opt/cloudbolt/rke/resource-101`.
This directory contains the authentication keys, `cluster.yml`, and `rkestate` for the Kubernetes cluster associated with that CloudBolt Resource ID.

## Setting up a CloudBolt Container Orchestrator

This action does not create a Kubernetes Container Orchestrator on the CloudBolt server.
To do this, run the following commands on the CloudBolt server:

1. SSH into your CloudBolt server (in HA setups, any servers should work).

2. `cd /path/to/rke/new-resource-id` (e.g., `/var/opt/cloudbolt/rke/resource-101`)

3. Run the following commands and save the output for later when we create a Container Orchestrator:

```
[1] $ export KUBECONFIG=/path/to/rke/new-resource-id/kube_config_cluster.yml
[2] $ export CB_KUBE_TOKEN=$(kubectl -n kube-system get secrets | grep cloudbolt-admin | awk '{print $1}')
[3] $ kubect get nodes -l node-role.kubernetes.io/controlplane=true
[4] $ kubectl -n kube-system get secret $CB_KUBE_TOKEN -o jsonpath='{.data.token}' | base64 -d
```

4. In CloudBolt, navigate to create a new Container Orchestrator.

5. Set the protocol to `HTTPS`.

6. Set the IP to be any of the IP addresses in the output of step `3`.

7. Set the Port to `6443`.

8. Use the output of step 4 as the Bearer Token Secret.