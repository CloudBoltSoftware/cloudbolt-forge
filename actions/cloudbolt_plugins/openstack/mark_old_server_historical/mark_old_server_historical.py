"""
This plug-in sets all OpenStack VMs back to historical if they've been added for more than 7d.
Cloudbolt, by default, sets all sync'ed VMs from OpenStack resource handler to Active 

Heavily based on aws/ignore_tagged_instances.py :)
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
from common.methods import set_progress
from infrastructure.models import Server
import datetime
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

def update_server_status(server):
    """
    Update the server status to 'HISTORICAL' if it's older than 7d
    """
    age = datetime.datetime.now() - server.add_date
    
    if age > datetime.timedelta(days=7):
        logger.info('Setting {} to HISTORICAL since it\'s older than 7d'.format(server))
        server.status = 'HISTORICAL'
        server.save()
        return True


def run(job, *args, **kwargs):
    set_progress("Setting all older OpenStack VMs to Historical.")

    # Example of how to fetch arguments passed to this plug-in ('server' will be available in
    # some cases)
    server = kwargs.get('server')
    if server:
        set_progress("This plug-in is running for server {}".format(server))

    set_progress("Dictionary of keyword args passed to this plug-in: {}".format(kwargs.items()))
    job_params = job.job_parameters.cast()
    openstack_rh = job_params.resource_handlers.filter(real_type__app_label="openstack")
    openstack_servers = Server.objects.filter(resource_handler__in=openstack_rh)
    num_changed = list( map(update_server_status, openstack_servers) ).count(True)
    set_progress('Updated {} OpenStack servers'.format(num_changed))
    
    if True:
        return "SUCCESS", "Older OpenStack servers set to historical", ""
    else:
        return "FAILURE", "Failed to set older Openstack servers to historical status", "All sync'ed VMs remain ACTIVE!"
