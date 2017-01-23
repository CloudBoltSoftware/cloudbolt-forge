"""
A post-sync-vms CB Plugin that updates all synced AWS servers with the
AWS tag 'CBStatus:Omit' as historical.
If the tag does not exist no changes are made to the CB server record.
"""
from infrastructure.models import Server
from utilities.logger import ThreadLogger
from common.methods import set_progress

TAG_NAME = 'CBStatus'
logger = ThreadLogger(__name__)

def get_server_status_tag(server):
    """
    Return the CB server status specified by this server's 'CBStatus' AWS tag or `None`
    if no tag exists on the server.
    """
    try:
        tags = server.ec2serverinfo.tags
        return tags.get(TAG_NAME)
    except Server.ec2serverinfo.RelatedObjectDoesNotExist as e:
        return None


def update_server_status(server):
    """
    Update the server status to 'HISTORICAL' if the tag exists, false otherwise.
    """
    status = get_server_status_tag(server)
    if not status:
        return False  # do nothing
    if status == 'Omit':
        logger.info('Changing status of server "{}" to HISTORICAL'.format(server))
        server.status = 'HISTORICAL'
        server.save()
        return True


def run(job, **kwargs):  # the job is the sync-vms job that causes this
    logger.job = job
    job_params = job.job_parameters.cast()
    aws_rhs = job_params.resource_handlers.filter(real_type__app_label='aws')
    aws_servers = Server.objects.filter(resource_handler__in=aws_rhs)
    set_progress('Updating AWS server status based on the "{}" tag value'.format(TAG_NAME))
    num_changed = map(update_server_status, aws_servers).count(True)
    set_progress('Updated {} AWS servers'.format(num_changed))
    return "", "", ""
