"""
Teardown service item action for AWS MySQL database.
foorbar2
"""
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
import time


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    db_identifier = resource.attributes.get(field__name='db_identifier').value
    print('DB IDENTIFIER: %s' % db_identifier)
    region = resource.attributes.get(field__name='aws_region').value
    rh_id = resource.attributes.get(field__name='aws_rh_id').value
    rh = AWSHandler.objects.get(id=rh_id)
    wrapper = rh.get_api_wrapper()

    set_progress('Connecting to Amazon RDS')
    rds = wrapper.get_boto3_client(
        'rds',
        rh.serviceaccount,
        rh.servicepasswd,
        region
    )

    set_progress('Deleting AWS MySQL database "{}"'.format(db_identifier))
    response = rds.delete_db_instance(
        DBInstanceIdentifier=db_identifier,
        SkipFinalSnapshot=True,
    )
    print(response)
    print(dir(response))

    # It takes awhile for the DB to be deleted
    while True:
        try:
            response = rds.describe_db_instances(DBInstanceIdentifier=db_identifier)
        except rds.exceptions.DBInstanceNotFoundFault:
            # Database is finally deleted
            set_progress('Database is now deleted')
            break

        db_instances = response['DBInstances']
        if len(db_instances) != 1:
            raise RuntimeError('Multiple database with identified "%" returned!' % db_identifier)

        db_instance = db_instances[0]
        status = db_instance['DBInstanceStatus']
        set_progress('Status of the database is: %s' % status)
        time.sleep(5)

    return "", "", ""
