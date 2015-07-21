"""
An example CloudBolt post-sync-vms hook script that sets the group on newly
synced servers that are on the associated datastore.

To use, first create a parameter for the group with a name that matches the
GROUP_DATASTORE_REGEX_CF value below. The term CF used throughout stands for
Custom Field, which is the same as a parameter. The value of the parameter
should be the name of the datastore you want to associate with the group. Note
that it must be a datastore and not a datastore cluster.
"""
import re

from resourcehandlers.vmware.models import VsphereResourceHandler
from orders.models import CustomFieldValue


GROUP_DATASTORE_REGEX_CF = "datastore_regex"


def get_cfv_group_mapping(cf_name):
    """
    Given a specific CF, create and return a dictionary mapping of values and the
    CloudBolt groups those values are associated with.
    """
    mapping = {}
    for cfv in CustomFieldValue.objects.filter(field__name=cf_name):
        # Assumption: Every group will have a unique datastore regex value
        group = cfv.group_set.first()
        if group and cfv.value not in mapping:
            mapping[cfv.value] = group
    return mapping


def get_datastore_for_server(server):
    """
    Given a server, return its datastore based on its first disk.
    """
    root_disk = server.disks.first()
    if root_disk:
        return root_disk.cast().datastore

    return None


def set_group_by_datastore(server, job, datastore_group_mapping):
    """
    Given a server, compare its datastore to the regex values used to map to
    groups and for any that match set the server's group accordingly.
    """
    datastore = get_datastore_for_server(server)
    if not datastore:
        return
    # Loop through the regex values and try to match
    for regex in datastore_group_mapping:
        if re.match(regex, datastore):
            group = datastore_group_mapping[regex]
            # Only need to set the group if it's not already set
            if group != server.group:
                job.set_progress("Adding server '{}' to group '{}'".format(
                    server, group))
                server.group = group
                server.save()


def run(job, logger=None):
    datastore_group_mapping = get_cfv_group_mapping(GROUP_DATASTORE_REGEX_CF)

    if not datastore_group_mapping:
        return "", "", ""

    jp = job.job_parameters.cast()
    job.set_progress(
        "Setting group on newly discovered servers based on their datastore"
    )
    # For each VMware VM try to set group
    for rh in jp.resource_handlers.all():
        rh = rh.cast()
        if not isinstance(rh, VsphereResourceHandler):
            continue
        job.set_progress("Adjusting group for servers in {}".format(rh.name))
        try:
            rh.verify_connection()
        except:
            job.set_progress("Failed to connect to {}... skipping it".format(rh.name))
            continue
        for server in rh.server_set.filter(status='ACTIVE'):
            set_group_by_datastore(server, job, datastore_group_mapping)

    return "", "", ""
