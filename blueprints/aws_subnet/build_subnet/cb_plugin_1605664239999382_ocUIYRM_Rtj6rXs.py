from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from resourcehandlers.aws.models import AWSHandler
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

AWS_ENVIRONMENT_ID = int('{{AWS_ENV_ID}}')
AWS_SUBNET_CIDR = str('{{AWS_SUBNET_CIDR}}')
AWS_AVAILABILITY_ZONE = str('{{AWS_AVAIL_ZONE}}')
AWS_VPC_CIDR = str('{{AWS_VPC_CIDR}}')


def generate_options_for_AWS_ENV_ID(
        profile,
        **kwargs):
    envs = Environment.objects_for_profile(profile)
    aws_envs = filter(
        lambda e: e.resource_handler and e.resource_handler.type_slug == 'aws',
        envs)

    options = []
    for env in list(aws_envs):
        options.append(
            (env.id, env.name),
        )

    return options


def generate_options_for_AWS_VPC_CIDR(
        control_field=None,
        form_data=None, form_prefix=None,
        **kwargs):
    options = []

    if not control_field:
        return options

    _, env_id = get_value_from_form_data(
        form_data=form_data,
        form_prefix=form_prefix,
        field_name='AWS_ENV_ID')

    try:
        env = Environment.objects.get(id=env_id)
        ec2_client = get_boto3_for_env(env)
        response = ec2_client.describe_vpcs(VpcIds=[env.vpc_id])
        if 'Vpcs' in response and len(response['Vpcs']) > 0:
            cidr = response['Vpcs'][0]['CidrBlock']
            options.append((cidr, cidr), )
    except Exception as ex:
        logger.error(ex)
        options.append(('not available', 'not available'), )

    return options


def get_value_from_form_data(
        form_data=None,
        form_prefix=None,
        field_name=None):
    field_key = None
    field_value = None
    if 'form_prefix' in form_data and not form_prefix:
        form_prefix = form_data.get('form_prefix', None)
    if not form_prefix:
        # Nothing can be found
        return field_key, field_value
    for key_name in form_data:
        if form_prefix + "-" + field_name + "_a" in key_name:
            field_key = key_name
            field_value = form_data[key_name] if \
                isinstance(form_data[key_name], str) else \
                form_data[key_name][0]
            break
    return field_key, field_value


def generate_options_for_AWS_AVAIL_ZONE(
        control_field=None,
        control_value=None,
        **kwargs):
    if not control_field:
        return []

    availability_zones = [
        ('default', 'Default'),
    ]

    try:
        env = Environment.objects.get(id=control_value)
        region = env.aws_region
        rh = AWSHandler.objects.get(id=env.resource_handler.id)
        ec2_client = rh.get_boto3_client(region_name=region)

        response = ec2_client.describe_availability_zones()
        if response.get('AvailabilityZones'):
            for zone in response['AvailabilityZones']:
                availability_zones.append(
                    (zone['ZoneName'], zone['ZoneName'],),
                )
    except Exception as ex:
        logger.error(ex)

    return availability_zones


def run(resource, profile, **kwargs):
    cf_subnet_id, _ = CustomField.objects.get_or_create(
        name="bp_aws_subnet_id",
        label="Subnet ID",
        type="STR",
        show_as_attribute=True
    )
    cf_subnet_cidr, _ = CustomField.objects.get_or_create(
        name="bp_aws_subnet_cidr",
        label="IPv4 CIDR Address",
        type="STR",
        show_as_attribute=True
    )
    cf_env_id, _ = CustomField.objects.get_or_create(
        name="bp_aws_subnet_env_id",
        label="CB Environment ID",
        type="INT",
        show_as_attribute=False
    )

    env = Environment.objects.get(id=AWS_ENVIRONMENT_ID)
    vpc_id = env.vpc_id
    region = env.aws_region
    rh = env.resource_handler.cast()
    ec2_client = rh.get_boto3_client(region_name=region)

    try:
        response = ec2_client.create_subnet(
            AvailabilityZone='' if AWS_AVAILABILITY_ZONE.lower() == 'default'
            else AWS_AVAILABILITY_ZONE,
            CidrBlock=AWS_SUBNET_CIDR,
            VpcId=vpc_id,
        )
        subnet_id = response['Subnet']['SubnetId']

        response = ec2_client.create_tags(
            Resources=[subnet_id],
            Tags=[
                {
                    "Key": "Name",
                    "Value": f"{resource.name}"
                },
                {
                    "Key": "cb_resource_id",
                    "Value": f"{resource.id}"
                },
                {
                    "Key": "cb_env_id",
                    "Value": f"{AWS_ENVIRONMENT_ID}"
                },
                {
                    "Key": "cb_rh_id",
                    "Value": f"{rh.id}"
                },
            ]
        )

        resource.update_cf_value(cf_subnet_id, subnet_id, profile)
        resource.update_cf_value(cf_subnet_cidr, AWS_SUBNET_CIDR, profile)
        resource.update_cf_value(cf_env_id, env.id, profile)

        set_progress(f"Subnet ID: {subnet_id}")
        set_progress(f"Subnet IPv4 CIDR: {AWS_SUBNET_CIDR}")
        set_progress(f"CB Environment ID: {env.id}")
    except Exception as ex:
        logger.error(ex)
        return "FAILURE", "", str(ex)

    return "SUCCESS", "", ""


def get_boto3_for_env(env):
    region = env.aws_region
    rh = env.resource_handler.cast()
    return rh.get_boto3_client(region_name=region)