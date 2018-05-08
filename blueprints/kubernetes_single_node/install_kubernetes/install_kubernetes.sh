#!/bin/bash -e

# Disable swap. Don't need to restart, this disables swap immediately
swapoff -a
sed -i 's/.*swap/#&/' /etc/fstab

# Setup Kubernetes repo
cat <<EOF > /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOF

# Disable SELinux (https://github.com/kubernetes/kubeadm/issues/417)
setenforce 0
sed -i 's/SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config

# Install dependencies
yum install -y kubelet kubeadm kubectl docker ipvsadm

# Set --selinux-enabled=false for Docker
sed '/OPTIONS=/s/--selinux-enabled /--selinux-enabled=false /' -i /etc/sysconfig/docker

# Install the Kubernetes version that matches the kubelet we installed from yum
K8S_VERSION=`kubelet --version | sed 's/Kubernetes //'`

# Enable services
systemctl enable kubelet
systemctl enable docker
systemctl start docker

# Configure iptables for kube-router
sysctl net.bridge.bridge-nf-call-iptables=1

cat <<EOF >  /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
EOF
sysctl --system

# Get the cgroup-driver from Docker and kubelet
DOCKER_CGROUP_DRIVER=$(docker info 2>/dev/null | grep "Cgroup Driver" | cut -f 2 -d ':' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
KUBELET_CGROUP_DRIVER=$(grep "cgroup-driver=" /etc/systemd/system/kubelet.service.d/10-kubeadm.conf | cut -f 4 -d "=" | tr -d '"')

if [ $DOCKER_CGROUP_DRIVER != $KUBELET_CGROUP_DRIVER ] ; then
  sed -i "s/cgroup-driver=${KUBELET_CGROUP_DRIVER}/cgroup-driver=${DOCKER_CGROUP_DRIVER}/g" /etc/systemd/system/kubelet.service.d/10-kubeadm.conf

  # In case kubelet is started with the wrong "cgroup-driver", the following will
  # restart kubelet with the correct one after the change above
  systemctl daemon-reload
  systemctl restart kubelet
fi

# Get Docker images so we don't have to rely on kubeadm to do it.
# This is a bit of a hack but it gets the kubeadm to not hang when downloading
# Docker images takes so long that kubeadm seems to forget what it's doing.
docker pull gcr.io/google_containers/pause-amd64:3.0
docker pull gcr.io/google_containers/etcd-amd64:3.1.11
docker pull gcr.io/google_containers/kube-proxy-amd64:${K8S_VERSION}
docker pull gcr.io/google_containers/kube-controller-manager-amd64:${K8S_VERSION}
docker pull gcr.io/google_containers/kube-scheduler-amd64:${K8S_VERSION}
docker pull gcr.io/google_containers/kube-apiserver-amd64:${K8S_VERSION}

# Initialize Kubernetes with 10.240.0.0/16 internal network (only if we haven't done this before)
if command -v kubeadm >/dev/null && kubeadm config view >/dev/null ; then
    echo "WARNING: kubeadm already exists and has valid config. 'kubeadm init' skipped"
else
    kubeadm init --pod-network-cidr=10.240.0.0/16 --kubernetes-version=${K8S_VERSION}
fi

# Set up the "root" kubectl config
mkdir -p $HOME/.kube
cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config

# Setup kube-router (https://github.com/cloudnativelabs/kube-router/blob/master/docs/kubeadm.md)
KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f https://raw.githubusercontent.com/cloudnativelabs/kube-router/master/daemonset/kubeadm-kuberouter-all-features.yaml
KUBECONFIG=/etc/kubernetes/admin.conf kubectl -n kube-system delete daemonset kube-proxy
docker run --privileged --net=host gcr.io/google_containers/kube-proxy-amd64:${K8S_VERSION} kube-proxy --cleanup-iptables

# Convert master into single machine cluster
kubectl taint nodes --all node-role.kubernetes.io/master-

# Install k8s dashboard
# TODO: we may be able to add "type: NodePort" to this file and have it immediately become
#       externally accessible instead of using the steps below.
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/master/src/deploy/recommended/kubernetes-dashboard.yaml

# Change dashboard to be externally accessible (from master node)
kubectl -n kube-system get service kubernetes-dashboard -o yaml | sed 's/ClusterIP/NodePort/' > dashboard.yaml
kubectl -n kube-system apply -f dashboard.yaml
rm -f dashboard.yaml