import json

from common.methods import set_progress
from infrastructure.models import Environment


def run(job, logger=None, **kwargs):
    service = job.resource_set.first()  # Change resource_set to service_set if you are using this script in CB version pre-8.0

    # The Environment ID and RDS Instance data dict were stored as attributes on
    # this service by a build action.
    env_id_cfv = service.attributes.get(field__name__startswith='aws_environment')
    instance_cfv = service.attributes.get(field__name='rds_instance')

    env = Environment.objects.get(id=env_id_cfv.value)
    client = connect_to_rds(env)

    instance = json.loads(instance_cfv.value)
    identifier = instance['identifier']

    job.set_progress('Deleting RDS instance {0}...'.format(identifier))
    client.delete_db_instance(
        DBInstanceIdentifier=identifier,
        # AWS strongly recommends taking a final snapshot before deleting a DB.
        # To do so, either set this to False or let the user choose by making it
        # a runtime action input (in that case be sure to set the param type to
        # Boolean so users get a dropdown).
        SkipFinalSnapshot=True,
    )

    job.set_progress('RDS instance {0} deleted.'.format(identifier))
    return 'SUCCESS', '', ''


def connect_to_rds(env):
    """
    Return boto connection to the RDS in the specified environment's region.
    """
    set_progress('Connecting to AWS RDS in region {0}.'.format(env.aws_region))
    rh = env.resource_handler.cast()
    wrapper = rh.get_api_wrapper()
    return wrapper.get_boto3_client(
        'rds',
        rh.serviceaccount,
        rh.servicepasswd,
        env.aws_region
    )
