#!/usr/bin/env python
"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
import hashlib
import time
import os
import string
import random

from common.methods import get_file_for_key_material
from common.methods import set_progress
from django.urls import reverse
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
import paramiko

from containerorchestrators.models import ContainerOrchestratorTechnology
from containerorchestrators.kuberneteshandler.models import Kubernetes
from infrastructure.models import CustomField, Server
from portals.models import PortalConfig

import re
import shutil
from tempfile import mkstemp

CLUSTER_NAME='{{ name }}'


def create_required_parameters():
    CustomField.objects.get_or_create(
        name='create_k8s_cluster_id',
        defaults=dict(
            label="Kubernetes Cluster: Cluster ID",
            description="Used by the Kubernetes Cluster blueprint",
            type="INT",
        ))
    CustomField.objects.get_or_create(
        name='create_k8s_cluster_dashboard_port',
        defaults=dict(
            label="Kubernetes Cluster: Dashboard Port",
            description="Used by the Kubernetes Cluster blueprint",
            type="INT",
        ))


def check_and_report_stderr(cmd, job, err):
    if err:
        job.set_progress("Error ({}): {}".format(cmd, err))

def run(job, *args, **kwargs):
    """
    Connect with the created Kubernetes Master and retrieve
    """
    resource = kwargs['resource']

    create_required_parameters()

    # Get private key to make requests to server
    job.set_progress("Retrieving credentials for Kubernetes master")
    server = job.server_set.last()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    creds = server.get_credentials()
    sudo = "sudo"

    if 'keyfile' in creds:
        filename, b = get_file_for_key_material(creds['keyfile'], server.resource_handler)
        key = paramiko.RSAKey.from_private_key_file(filename)
        c.connect(hostname=server.ip, username=creds['username'], pkey=key)
    else:
        c.connect(hostname=server.ip, username=creds['username'], password=creds['password'], banner_timeout=60)

    if creds['username'] == "root":
        sudo = ""

    job.set_progress("Connected to master")

    # Get dashboard port
    job.set_progress('Getting dashboard port')
    cmd = "{} kubectl -n kube-system get service/kubernetes-dashboard -o jsonpath={}".format(sudo, "{.spec.ports[0].nodePort}")
    stdin, stdout, stderr = c.exec_command(cmd)
    port = stdout.read()
    check_and_report_stderr(cmd, job, stderr.read())
    resource.create_k8s_cluster_dashboard_port = port
    resource.save()

    # Create the k8s service account and cluster role binding.
    # Then get the token associated with the account to use as a Bearer token.
    job.set_progress('Creating the Kubernetes admin service account')

    cmd = "{} kubectl create serviceaccount kube-admin --namespace kube-system".format(sudo)
    stdin, stdout, stderr = c.exec_command(cmd)
    check_and_report_stderr(cmd, job, stderr.read().decode('utf8'))
    cmd = "{} echo 'kind: ClusterRoleBinding\napiVersion: rbac.authorization.k8s.io/v1beta1\nmetadata:\n  name: kube-admin-clusterrolebinding\nsubjects:\n- kind: ServiceAccount\n  name: kube-admin\n  namespace: kube-system\nroleRef:\n  kind: ClusterRole\n  name: cluster-admin\n  apiGroup: \"\"' > /tmp/binding.yaml".format(sudo)
    stdin, stdout, stderr = c.exec_command(cmd)
    check_and_report_stderr(cmd, job, stderr.read().decode('utf8'))
    cmd = "{} kubectl create -f /tmp/binding.yaml".format(sudo)
    stdin, stdout, stderr = c.exec_command(cmd)
    check_and_report_stderr(cmd, job, stderr.read().decode('utf8'))
    cmd = "{} kubectl get secrets $(sudo kubectl get secrets -n kube-system | grep kube-admin-token- | tr -s ' ' | cut -f 1 -d ' ') -n kube-system -o custom-columns=:.data.token | base64 -d".format(sudo)
    stdin, stdout, stderr = c.exec_command(cmd)
    bearer_token = stdout.read().decode('utf8')
    check_and_report_stderr(cmd, job, stderr.read().decode('utf8'))

    # Close the client
    c.close()

    # Save the Kubernetes information in CB
    job.set_progress('Creating container orchestrator')
    tech = ContainerOrchestratorTechnology.objects.get(name='Kubernetes')
    kubernetes = Kubernetes.objects.create(
        name=CLUSTER_NAME,
        ip=server.ip,
        port=6443,
        protocol='https',
        serviceaccount="kube-admin",
        servicepasswd=bearer_token,
        auth_type='TOKEN',
        container_technology=tech
    )

    # Save ID on the resource so it can be deleted during teardown later
    resource.create_k8s_cluster_id = kubernetes.id
    resource.save()

    url = 'https://{}:{}'.format(server.ip, port)
    job.set_progress("Dashboard URL: {}".format(url))

    return None