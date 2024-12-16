#!/bin/bash

# Update system
yum update -y

# Disable SELinux
setenforce 0
sed -i --follow-symlinks 's/^SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config

# Enable br_netfilter for Kubernetes networking
modprobe br_netfilter
echo '1' | tee /proc/sys/net/bridge/bridge-nf-call-iptables
echo '1' | tee /proc/sys/net/bridge/bridge-nf-call-ip6tables

# Install container runtime (CRI-O)
yum install -y yum-utils
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y containerd.io --allowerasing
systemctl start containerd
systemctl enable containerd

# Add Kubernetes repo
cat <<EOF | tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.31/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.31/rpm/repodata/repomd.xml.key
EOF

# Install Kubernetes components
yum install -y kubelet kubeadm kubectl
systemctl enable kubelet --now

# Disable swap
swapoff -a
sed -i '/swap/d' /etc/fstab

# Open necessary ports in firewalld
firewall-cmd --permanent --add-port=6443/tcp
firewall-cmd --permanent --add-port=10250/tcp
firewall-cmd --reload

# Install tc command
yum install -y iproute-tc

# Enable IP forwarding
echo '1' | tee /proc/sys/net/ipv4/ip_forward

# Pull the recommended sandbox image
ctr image pull registry.k8s.io/pause:3.10
ctr image tag registry.k8s.io/pause:3.10 registry.k8s.io/pause:3.6

# Set up containerd
containerd config default > /etc/containerd/config.toml
systemctl restart containerd

# Initialize the Kubernetes cluster
kubeadm init --pod-network-cidr=192.168.0.0/16

# Check if kubeadm init was successful
if [ $? -ne 0 ]; then
    echo "kubeadm init failed. Please check the output for errors."
    exit 1
fi

# Configure kubectl for the root user
mkdir -p $HOME/.kube
cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config

# Deploy a CNI (Calico in this case)
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Print the join command for worker nodes
kubeadm token create --print-join-command > /tmp/kubeadm_join_command.sh

echo "Control plane setup is complete. Join command saved to /tmp/kubeadm_join_command.sh"