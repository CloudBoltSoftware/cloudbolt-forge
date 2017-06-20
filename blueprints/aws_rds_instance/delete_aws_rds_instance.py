import json
import boto3

from infrastructure.models import Environment


def run(job, logger=None, **kwargs):
    service = job.service_set.first()
    env_id = service.attributes.get(field__name__startswith='aws_environment').value
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()

    job.set_progress('Connecting to AWS...')
    client = boto3.client(
        'rds',
        region_name=env.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd)

    instance_cfv = service.attributes.get(field__name='rds_instance')
    instance = json.loads(instance_cfv.value)
    identifier = instance['identifier']

    job.set_progress('Deleting RDS instance {}...'.format(identifier))
    response = client.delete_db_instance(
        DBInstanceIdentifier=identifier,
        # AWS strongly recommends taking a final snapshot before deleting a DB.
        # To do so, either set this to False or let the user choose by making it
        # a runtime action input (in that case be sure to set the param type to
        # Boolean so users get a dropdown).
        SkipFinalSnapshot=True,
    )

    job.set_progress('RDS instance {0} deleted.'.format(identifier))
    return 'SUCCESS', '', ''
