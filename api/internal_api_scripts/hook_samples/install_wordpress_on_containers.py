#!/usr/local/bin/python

import requests

from oauth2client.client import SignedJwtAssertionCredentials
from apiclient.discovery import build
import time

from resourcehandlers.gce.models import GCEHandler
from utilities.helpers import get_ssl_verification

BASE_NAME = "btestcapi"
KUB_USERNAME = "root"
KUB_PASSWORD = "cloudbolt"


def get_apis():
    gce = GCEHandler.objects.first()

    keyfile_path = gce.servicepasswd
    key = file(keyfile_path, 'rb').read()
    project = gce.project

    # use the first env's zone (node_location) for now
    e = gce.environment_set.first()
    zone = e.node_location

    credentials = SignedJwtAssertionCredentials(
        gce.serviceaccount, key,
        scope=['https://www.googleapis.com/auth/cloud-platform'])
    containerapi = build('container', 'v1beta1', credentials=credentials)

    credentials = SignedJwtAssertionCredentials(
        gce.serviceaccount, key,
        scope=['https://www.googleapis.com/auth/compute'])
    computeapi = build('compute', 'v1', credentials=credentials)

    return computeapi, containerapi, project, zone


def _wait_for_cluster_creation(job, get_cluster_func):
    endpoint = None
    while not endpoint:
        job.set_progress("Waiting for Kubernetes cluster creation to complete")
        time.sleep(5)
        cluster = get_cluster_func()
        if "endpoint" in cluster:
            endpoint = cluster['endpoint']
        # TODO: add a timeout
    return cluster


def create_cluster(job, containerapi, project, zone):
    """
    :return: 2-tuple: (the name of the new cluster, the IP of the Kubernetes API endpoint)
    """
    clusters = containerapi.projects().zones().clusters()
    name = "{}-{}".format(BASE_NAME, int(time.time()))
    print "Creating cluster with name {}".format(name)

    clusters.create(
        projectId=project, zoneId=zone,
        body={
            "cluster": {
                "numNodes": 1, "machineType": "g1-small", "name": name,
                "masterAuth": {"user": KUB_USERNAME, "password": KUB_PASSWORD}
            }
        }).execute()

    get_cluster = clusters.get(
        projectId=project, zoneId=zone,
        clusterId=name).execute
    cluster = _wait_for_cluster_creation(job, get_cluster)

    return name, cluster['endpoint']


def create_pod(kubernetes_ip):
    wordpress_pod_dict = {
        "id": "wordpress",
        "kind": "Pod",
        "apiVersion": "v1beta1",
        "desiredState": {
            "manifest": {
                "version": "v1beta1",
                "containers": [{
                    "name": "wordpress",
                    "image": "tutum/wordpress",
                    "ports": [{
                        "containerPort": 80,
                        "hostPort": 80
                    }]
                }]
            }
        }
    }
    requests.post(
        'https://{}/api/v1beta3/namespaces/default/pods'.format(kubernetes_ip),
        auth=(KUB_USERNAME, KUB_PASSWORD), verify=get_ssl_verification(), json=wordpress_pod_dict)


def enable_http(computeapi, project, cluster_name):
    tag_name = "k8s-{}-node".format(cluster_name)
    # TODO: switch node_name to the tag (remove the -1 or whatever)
    fwd = {
        'allowed': [{'IPProtocol': 'tcp', 'ports': ['80']}],
        'kind': 'compute#firewall',
        'name': '{}-http'.format(tag_name),
        'sourceRanges': ['0.0.0.0/0'],
        'targetTags': [tag_name]}

    computeapi.firewalls().insert(project=project, body=fwd).execute()
    # TODO check http response


def run(job, *args, **kwargs):
    job.set_progress("Connecting to GCE", 1, 4)
    computeapi, containerapi, project, zone = get_apis()

    job.set_progress("Creating the cluster", 2)
    cluster_name, kubernetes_ip = create_cluster(
        job, containerapi, project, zone)

    job.set_progress("Creating the pod", 3)
    create_pod(kubernetes_ip)

    job.set_progress("Configuring firewall to enable HTTP traffic")
    enable_http(computeapi, project, cluster_name)
    job.set_progress("Successfully deployed Wordpress to a new container pod", 4)

    # TODO: get the node IP at some point above and write it to the progress
    return "", "", ""


if __name__ == '__main__':
    import sys
    from jobs.models import Job
    job_id = sys.argv[1]
    job = Job.objects.get(id=job_id)
    job.status = 'SUCCESS'
    job.save()
    print run(job)
