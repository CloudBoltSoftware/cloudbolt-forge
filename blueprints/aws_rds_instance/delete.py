from common.methods import set_progress
from infrastructure.models import Environment
from resourcehandlers.aws.models import AWSHandler
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

def get_aws_rh_and_region(resource):
    # The AWS Handler ID and AWS region were stored as attributes
    # this service by a build/sync action.
    rh_aws_id = resource.aws_rh_id
    aws_region =  resource.aws_region
    rh_aws = None

    if rh_aws_id is not None or rh_aws_id != "":
        rh_aws = AWSHandler.objects.filter(id=rh_aws_id).first()

    if aws_region is not None or rh_aws_id != "":
        # this is deprecated, will be removed next release
        env_id_cfv = resource.attributes.filter(field__name__startswith='aws_environment').first()
        
        if env_id_cfv is None:
            return aws_region, rh_aws
            
        env = Environment.objects.get(id=env_id_cfv.value)
        aws_region = env.aws_region

        if rh_aws is None:
            rh_aws = env.resource_handler.cast()

    return aws_region, rh_aws


def run(job, logger=None, **kwargs):
    resource = kwargs.pop('resources').first()

    set_progress(f"RDS instance Delete plugin running for resource: {resource}")
    logger.info(f"RDS instance Delete plugin running for resource: {resource}")
    
    rds_instance_identifier = resource.db_identifier
    
    # get aws region and resource handler object
    region, aws, = get_aws_rh_and_region(resource)

    if aws is None or aws == "":
        return "WARNING", "", "Need a valid aws region to delete this database"

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
    
    try:
        # verify rds db instance
        rds_resp = client.describe_db_instances(DBInstanceIdentifier=rds_instance_identifier)
    except Exception as err:
        if "DBInstanceNotFound" in str(err):
            return "WARNING", f"RDS db instance {rds_instance_identifier} not found, it may have already been deleted", ""
        raise RuntimeError(err)
    
    job.set_progress('Deleting RDS instance {0}...'.format(rds_instance_identifier))
    
    # delete RDS instance from AWS
    client.delete_db_instance(
        DBInstanceIdentifier=rds_instance_identifier,
        # AWS strongly recommends taking a final snapshot before deleting a DB.
        # To do so, either set this to False or let the user choose by making it
        # a runtime action input (in that case be sure to set the param type to
        # Boolean so users get a dropdown).
        SkipFinalSnapshot=True,
        DeleteAutomatedBackups=True,
    )
    
    if resource.db_cluster_identifier != "":
        try:
            # delete rds db cluster
            client.delete_db_cluster(DBClusterIdentifier=resource.db_cluster_identifier,
                                                                SkipFinalSnapshot=True)
        except Exception as err:
            pass

    job.set_progress(f"RDS instance {rds_instance_identifier} deleted successfully")
    
    return 'SUCCESS', f"RDS instance {rds_instance_identifier} deleted successfully", ''