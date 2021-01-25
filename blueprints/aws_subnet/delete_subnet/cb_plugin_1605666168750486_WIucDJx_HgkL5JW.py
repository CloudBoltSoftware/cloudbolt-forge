from common.methods import set_progress
from infrastructure.models import Environment
from resourcehandlers.aws.models import AWSHandler
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def run(job, resource, profile, **kwargs):
    set_progress("Delete Customer Subnet")

    env_id = resource.bp_aws_subnet_env_id
    subnet_id = resource.bp_aws_subnet_id

    try:
        env = Environment.objects.get(id=env_id)
        rh = env.resource_handler.cast()
        ec2_client = rh.get_boto3_client(region_name=env.aws_region)
        response = ec2_client.delete_subnet(SubnetId=subnet_id)
    except Exception as ex:
        logger.error(str(ex))
        return "WARNING", "", f"Unable to remove subnet: {subnet_id}. " \
                              f"Manual clean-up in AWS may be necessary."

    return "SUCCESS", "", ""