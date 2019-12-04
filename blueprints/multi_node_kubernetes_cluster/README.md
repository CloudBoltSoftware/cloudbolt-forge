# Deploy Multi Node Kubernetes Cluster Blueprint

This deployment builds, configures and deploys a kubernetes cluster to one or many servers.

## Usage

### Servers
1.  Server(s) must be added as a build item(s) before the Deploy Kubernetes Cluster plugin.
2.  Each server must have a minimum of 1 cpu and a Mem Size of 2

## Deployment Specifics
This Blueprint will deploy a kubernetes cluster to the set of servers provisioned in the build process. Note that the master node (kubernetes api) is deployed to the first server.

This can sometimes take updwards of 20 minutes, depending on number of servers. The Deploy Kubernetes Cluster plugin included with this Blueprint will configure each server individually.

CloudBolt Kubernetes clusters are closely associated with the Resource/Service created when the server(s) are provisioned. The Resource ID is used to identify kubernetes conigurations specific to that resource.

### RKE

This Blueprint utilizes RKE to configure and deploy the kubernetes cluster.

RKE will be included with Cloudbolt versions 9.2+
This plugin assumes an `rke` executable exists in the CloudBolt server `root` user's path;
e.g., at `/usr/local/bin/rke`.
See https://github.com/rancher/rke/releases for more information on RKE.

### kubectl

This Blueprint utilizes kubectl to manage existing kubernetes clusters

kubectl will be included with Cloudbolt versions 9.2+
See https://kubernetes.io/docs/tasks/tools/install-kubectl/ for more information on kubectl.


## Teardown
When the resource/service is deleted:
    All kubernetes cluster configurations associated with the resource will be delete.
    The container orchestrator created for the Kubernetes cluster will be deleted.



