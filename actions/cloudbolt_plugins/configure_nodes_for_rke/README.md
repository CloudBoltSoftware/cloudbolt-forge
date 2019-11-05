This plugin will build and deploy a vanilla kubernetes cluster to each server supplied in the blueprint.

You will need to manually install rke. See https://github.com/rancher/rke/releases. This plugin assumes an rke executable in the '/var/opt/cloudbolt/rke/' path.

This plugin allows for multiple clusters. Configuration for each cluster is based off of the resource associated with the deployed blueprint.
'/var/opt/cloudbolt/rke/resource-101' for example will contain the keys, cluster.yml, rkestate for a cluster associated with resource with id of 101.