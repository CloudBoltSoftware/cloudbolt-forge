#!/bin/sh

# This automates the instructions for installation described here:
# https://wiki.jenkins-ci.org/display/JENKINS/Installing+Jenkins+on+Red+Hat+distributions

# Install prereqs: wget, and the version of Java required for Jenkins
yum install -y wget
yum remove -y java
yum install -y java-1.7.0-openjdk

# Install Jenkins
wget -O /etc/yum.repos.d/jenkins.repo http://pkg.jenkins-ci.org/redhat-stable/jenkins.repo
rpm --import https://jenkins-ci.org/redhat/jenkins-ci.org.key
yum install -y jenkins

# Start Jenkins and make sure it starts when the system boots
service jenkins start
chkconfig jenkins on

# Turn off the firewall on this server so users can get to the Jenkins UI
service iptables stop
chkconfig iptables off