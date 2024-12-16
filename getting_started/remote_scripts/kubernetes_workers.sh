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

# Pull the recommended sandbox image
ctr image pull registry.k8s.io/pause:3.10
ctr image tag registry.k8s.io/pause:3.10 registry.k8s.io/pause:3.6

# Set up containerd
containerd config default > /etc/containerd/config.toml
systemctl restart containerd

# Enable IP Forwarding
if grep -q '^net.ipv4.ip_forward' /etc/sysctl.conf; then
    sed -i 's/^net.ipv4.ip_forward.*/net.ipv4.ip_forward = 1/' /etc/sysctl.conf
else
    echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
fi
sysctl -p

# Run the join command (replace with the actual command from the control plane)
{{ server.k8s_join_command }}

echo "Worker node setup is complete."