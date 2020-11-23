from common.methods import set_progress
from infrastructure.models import Environment
from resourcehandlers.aws.models import AWSHandler


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    rds_instance_identifier = resource.db_identifier

    # The Environment ID and RDS Instance data dict were stored as attributes on
    # this service by a build action.
    aws_id = resource.aws_rh_id
    env_id_cfv = resource.attributes.filter(field__name__startswith='aws_environment').first()

    region = resource.aws_region
    aws = None
    if aws_id:
        aws = AWSHandler.objects.get(id=aws_id)
    if not region and env_id_cfv:
        env = Environment.objects.get(id=env_id_cfv.value)
        region = env.aws_region
        aws = env.resource_handler.cast()

    if not region:
        return "FAILURE", "", "Need a valid aws region to delete this database"

    set_progress('Connecting to Amazon RDS')
    wrapper = aws.get_api_wrapper()
    client = wrapper.get_boto3_client(
        'rds',
        aws.serviceaccount,
        aws.servicepasswd,
        region
    )

    job.set_progress('Deleting RDS instance {0}...'.format(rds_instance_identifier))
    client.delete_db_instance(
        DBInstanceIdentifier=rds_instance_identifier,
        # AWS strongly recommends taking a final snapshot before deleting a DB.
        # To do so, either set this to False or let the user choose by making it
        # a runtime action input (in that case be sure to set the param type to
        # Boolean so users get a dropdown).
        SkipFinalSnapshot=True,
    )

    job.set_progress('RDS instance {0} deleted.'.format(rds_instance_identifier))
    return 'SUCCESS', '', ''
