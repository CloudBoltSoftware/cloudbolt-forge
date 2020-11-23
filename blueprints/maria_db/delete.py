"""
Teardown service item action for AWS MariaDB database.
"""
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
import boto3
import time


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    db_identifier = resource.attributes.get(field__name='db_identifier').value
    region = resource.attributes.get(field__name='aws_region').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    rh = AWSHandler.objects.get(id=rh_id)

    set_progress('Connecting to Amazon RDS')
    rds = boto3.client('rds',
                       region_name=region,
                       aws_access_key_id=rh.serviceaccount,
                       aws_secret_access_key=rh.servicepasswd
                       )

    set_progress('Deleting AWS MariaDB database "{}"'.format(db_identifier))
    response = rds.delete_db_instance(
        DBInstanceIdentifier=db_identifier,
        SkipFinalSnapshot=True,
    )

    # It takes awhile for the DB to be deleted
    while True:
        try:
            response = rds.describe_db_instances(
                DBInstanceIdentifier=db_identifier)
        except rds.exceptions.DBInstanceNotFoundFault:
            # Database is finally deleted
            set_progress('Database is now deleted')
            break

        db_instances = response['DBInstances']

        db_instance = db_instances[0]
        status = db_instance['DBInstanceStatus']
        set_progress('Status of the database is: %s' % status)
        time.sleep(5)

    return "", "", ""
