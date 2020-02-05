"""
This service action is intended to be used as a management action on the AWS
RDS Instance blueprint. Importing the blueprint from the CloudBolt Content
Library will automatically import this action.
"""
import json

from common.methods import set_progress
from infrastructure.models import Environment
from orders.models import CustomFieldValue


def run(job, logger=None, **kwargs):
    service = job.resource_set.first()  # Replace resource_set to service_set if you are using this script in CB version pre-8.0

    # The Environment ID and RDS Instance data dict were stored as attributes on
    # this service by a build action.
    env_id_cfv = service.attributes.get(field__name__startswith='aws_environment')
    instance_cfv = service.attributes.get(field__name='rds_instance')

    env = Environment.objects.get(id=env_id_cfv.value)
    client = connect_to_rds(env)

    instance = json.loads(instance_cfv.value)
    identifier = instance['identifier']

    job.set_progress('Refreshing RDS instance {0}...'.format(identifier))
    response = client.describe_db_instances(DBInstanceIdentifier=identifier)

    boto_instance = response['DBInstances'][0]
    instance = boto_instance_to_dict(boto_instance)
    replace_instance_data_on_service(instance, instance_cfv, service)

    job.set_progress('RDS instance {0} updated.'.format(identifier))
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


def boto_instance_to_dict(boto_instance):
    """
    Create a pared-down representation of an RDS instance from the full boto
    dictionary.
    """
    instance = {
        'identifier': boto_instance['DBInstanceIdentifier'],
        'engine': boto_instance['Engine'],
        'status': boto_instance['DBInstanceStatus'],
        'username': boto_instance['MasterUsername'],
    }
    # Endpoint may not be returned if networking is not set up yet
    endpoint = boto_instance.get('Endpoint', {})
    instance.update({
        'address': endpoint.get('Address'),
        'port': endpoint.get('Port')
    })
    return instance


def replace_instance_data_on_service(instance, instance_cfv, service):
    """
    To update the RDS Instance attribute on this service, the previous one is
    removed and a new JSON CFV is added.
    """
    new_instance_cfv, _ = CustomFieldValue.objects.get_or_create(
        field__name='rds_instance', value=json.dumps(instance))
    service.attributes.remove(instance_cfv)
    service.attributes.add(new_instance_cfv)

    # Also remove the previous CFV from CB since it is no longer valid
    instance_cfv.delete()
