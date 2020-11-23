import json
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from botocore.client import ClientError

RESOURCE_IDENTIFIER = 'db_identifier'


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


def discover_resources(**kwargs):
    discovered_rds_instances = []

    for handler in AWSHandler.objects.all():
        try:
            wrapper = handler.get_api_wrapper()
            set_progress('Connecting to Amazon RDS Instance for handler: {}'.format(handler))
        except Exception as e:
            set_progress(f"Could not get wrapper: {e}")
            continue

        for region in handler.current_regions():
            rds = wrapper.get_boto3_client(
                'rds',
                handler.serviceaccount,
                handler.servicepasswd,
                region
            )

            try:
                for instance in rds.describe_db_instances()['DBInstances']:
                    instance_dict = boto_instance_to_dict(instance)
                    discovered_rds_instances.append({
                        'db_identifier': instance['DBInstanceIdentifier'],
                        'aws_region': region,
                        'aws_rh_id': handler.id,
                        'rds_instance': json.dumps(instance_dict)
                    })
            except ClientError as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return discovered_rds_instances
