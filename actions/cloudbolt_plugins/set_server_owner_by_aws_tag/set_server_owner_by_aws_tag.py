"""
A post-sync-vms CloudBolt Plugin that updates the owner of all
synced AWS servers to the CB user that has the username in the AWS tag
'VM_Owner'.

If the VM_Owner tag does not exist, or if the named user does not exist in CB,
no changes are made to the CB server record.
"""

from accounts.models import UserProfile
from infrastructure.models import Server
from utilities.logger import ThreadLogger
from common.methods import set_progress


TAG_NAME = 'VM_Owner'
logger = ThreadLogger(__name__)


def update_server_owner(server):
    """
    Update the owner of AWS `server` to be the CB user having the same username
    as the server's AWS tag 'VM_Owner'. Returns `True` if the server is
    modified, False otherwise.
    """

    username = username_from_server_tags(server)
    if not username:
        return False  # do nothing, not even unset a user if no owner tag is set

    user = get_cb_user(username)

    # If it is desired to create a user if one does not already exist, then the
    # above `get_cb_user` function could be augmented into a `get_or_create_user`
    # function, and this if-block removed.
    if not user:
        logger.info(
            'User "{}" tagged as owner for server "{}", but no such user '
            'exists in CB'.format(username, server))
        return False

    if server.owner != user:
        logger.info('Changing the owner of server "{}" from "{}" to "{}"'.format(
            server, server.owner, user))
        server.owner = user
        server.save()
        return True


def username_from_server_tags(server):
    """
    Return the username specified by this server's 'VM_Owner' AWS tag or `None`
    if no tag exists on the server.
    """
    tags = server.ec2serverinfo.tags
    return tags.get(TAG_NAME)


def get_cb_user(username):
    """
    Return a CB user matching `username`, or `None` if no user can be
    unambiguously selected by username alone.
    """
    try:
        return UserProfile.objects.get(user__username=username)
    except (UserProfile.DoesNotExist, UserProfile.MultipleObjectsReturned):
        return None


def run(job, **kwargs):  # the job is the sync-vms job that causes this
    logger.job = job

    job_params = job.job_parameters.cast()
    aws_rhs = job_params.resource_handlers.filter(real_type__app_label='aws')
    aws_servers = Server.objects.filter(resource_handler__in=aws_rhs)

    set_progress('Updating AWS server owners based on the "{}" tag value'.format(TAG_NAME))
    num_changed = map(update_server_owner, aws_servers).count(True)
    set_progress('Updated {} AWS server owners'.format(num_changed))

    return "", "", ""
