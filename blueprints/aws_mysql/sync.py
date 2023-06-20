from botocore.client import ClientError
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler


RESOURCE_IDENTIFIER = 'db_identifier'


def discover_resources(**kwargs):
    discovered_mysql = []
    for handler in AWSHandler.objects.all():
        wrapper = handler.get_api_wrapper()
        set_progress('Connecting to Amazon RDS for handler: {}'.format(handler))
        for region in handler.current_regions():
            rds = wrapper.get_boto3_client(
                'rds',
                handler.serviceaccount,
                handler.servicepasswd,
                region
            )
            try:
                for db_instance in rds.describe_db_instances()['DBInstances']:
                    if db_instance['Engine'] == 'mysql':
                        discovered_mysql.append({
                            'db_identifier': db_instance['DBInstanceIdentifier'],
                            "aws_region": region,
                            "aws_rh_id": handler.id
                        })
            except ClientError as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return discovered_mysql
