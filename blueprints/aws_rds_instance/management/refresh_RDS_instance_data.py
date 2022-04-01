"""
This service action is intended to be used as a management action on the AWS
RDS Instance blueprint. Importing the blueprint from the CloudBolt Content
Library will automatically import this action.
"""

from common.methods import set_progress
from infrastructure.models import Environment, CustomField
from resourcehandlers.aws.models import AWSHandler
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

def get_or_create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='db_endpoint_address',
        defaults={
            "label": 'Endpoint Address',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint',
            "show_on_servers": True
        }
    )

    CustomField.objects.get_or_create(
        name='db_endpoint_port',
        defaults={
            "label": 'Endpoint Port',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint',
            "show_on_servers": True
        }
    )

    CustomField.objects.get_or_create(
        name='db_subnets',
        defaults={
            "label": 'Subnets',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint',
            "show_on_servers": True
        }
    )

    CustomField.objects.get_or_create(
        name='db_username',
        defaults={
            "label": 'Username',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint',
            "show_on_servers": True
        }
    )

def get_aws_rh_and_region(resource):
    # The AWS Handler ID and AWS region were stored as attributes
    # this service by a build/sync action.
    rh_aws_id = resource.aws_rh_id
    aws_region =  resource.aws_region
    rh_aws = None

    if rh_aws_id != "" or rh_aws_id is not None:
        rh_aws = AWSHandler.objects.get(id=rh_aws_id)

    if aws_region != "" or aws_region is not None:
        # this is deprecated, will be removed later
        env_id_cfv = resource.attributes.filter(field__name__startswith='aws_environment').first()
        
        if env_id_cfv is None:
            return aws_region, rh_aws
            
        env = Environment.objects.get(id=env_id_cfv.value)
        aws_region = env.aws_region

        if rh_aws is None:
            rh_aws = env.resource_handler.cast()

    return aws_region, rh_aws
    
def boto_instance_to_dict(boto_instance, region, handler):
    """
    Create a pared-down representation of an RDS instance from the full boto
    dictionary.
    """
    instance = {
        'aws_region': region,
        'aws_rh_id': handler.id,
        'db_identifier': boto_instance['DBInstanceIdentifier'],
        'db_engine': boto_instance['Engine'],
        'db_status': boto_instance['DBInstanceStatus'],
        'db_username': boto_instance['MasterUsername'],
        'db_publicly_accessible': boto_instance['PubliclyAccessible'],
        'db_availability_zone': boto_instance['AvailabilityZone']
    }

    # get subnet object
    subnet_group = boto_instance.get("DBSubnetGroup", {})

    # Endpoint may not be returned if networking is not set up yet
    endpoint = boto_instance.get('Endpoint', {})

    instance.update({'db_endpoint_address': endpoint.get('Address'), 
        'db_endpoint_port': endpoint.get('Port'), 
        'db_subnet_group': subnet_group.get("DBSubnetGroupName"),
        'db_subnets': [xx['SubnetIdentifier'] for xx in subnet_group.get("Subnets", [])]})

    logger.info(f"Updates RDS instance: {instance}")

    return instance
    
def run(job, resource, logger=None, **kwargs):
    # The Environment ID and RDS Instance data dict were stored as attributes on
    # this service by a build action.
    rds_instance_identifier = resource.db_identifier

    # get aws region and resource handler object
    region, aws, = get_aws_rh_and_region(resource)

    if aws is None or aws == "":
        return  "WARNING", f"RDS db instance {rds_instance_identifier} not found, it may have already been deleted", ""

    # get or create custom fields
    get_or_create_custom_fields_as_needed()

    set_progress('Connecting to Amazon RDS')
    
    # get aws resource handler wrapper object
    wrapper = aws.get_api_wrapper()

    # initialize boto3 client
    client = wrapper.get_boto3_client(
                    'rds',
                    aws.serviceaccount,
                    aws.servicepasswd,
                    region
                )

    job.set_progress('Refreshing RDS instance {0}...'.format(rds_instance_identifier))

    # fetch rds db instance
    rds_rsp = client.describe_db_instances(DBInstanceIdentifier=rds_instance_identifier)['DBInstances']

    if not rds_rsp:
        return  "WARNING", f"RDS db instance {rds_instance_identifier} not found, it may have already been deleted", ""


    # convert rds db instance to dict
    rds_instance = boto_instance_to_dict(rds_rsp[0], region, aws)

    for key, value in rds_instance.items():
        setattr(resource, key, value) # set custom field value

    resource.save()

    job.set_progress('RDS instance {0} updated.'.format(rds_instance_identifier))

    return 'SUCCESS', f'RDS instance {rds_instance_identifier} updated successfully.', ''