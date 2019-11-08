This plugin will build and deploy a vanilla Kubernetes cluster onto the servers provisioned in a Blueprint. Each server will be assigned one or more roles from: API server, worker, and etcd.

You will need to manually install `rke` to your CloudBolt server. See https://github.com/rancher/rke/releases for insructions. This plugin assumes an `rke` executable exists in the '/var/opt/cloudbolt/rke/bin/' directory.

This plugin allows for multiple clusters. Configuration for each cluster is based off of the resource associated with the deployed blueprint.
'/var/opt/cloudbolt/rke/resource-101' for example will contain the keys, `cluster.yml`,` rkestate` for a cluster associated with a CloudBolt resource with id of 101.
