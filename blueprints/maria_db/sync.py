"""
Discover MariaDB records with some identifying attributes
return a list of dictionaries from the 'discover_resoures' function
"""
import boto3
from botocore.client import ClientError
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler

RESOURCE_IDENTIFIER = 'db_identifier'


def discover_resources(**kwargs):
    discovered_mariadb = []

    for handler in AWSHandler.objects.all():
        set_progress('Connecting to Amazon Maria DB for \
                      handler: {}'.format(handler))
        for region in handler.current_regions():
            rds = boto3.client(
                'rds',
                region_name=region,
                aws_access_key_id=handler.serviceaccount,
                aws_secret_access_key=handler.servicepasswd
            )
            try:
                for db in rds.describe_db_instances()['DBInstances']:
                    if db['Engine'] == 'mariadb':
                        discovered_mariadb.append(
                            {
                                'name': 'RDS MariaDB - ' + db['DBInstanceIdentifier'],
                                'db_address': db['Endpoint']['Address'],
                                'db_port': db['Endpoint']['Port'],
                                'db_identifier': db['DBInstanceIdentifier'],
                                'aws_rh_id': handler.id,
                                'aws_region': region
                            }
                        )
            except ClientError as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return discovered_mariadb
