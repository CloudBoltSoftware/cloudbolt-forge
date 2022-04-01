"""
Action creates a new RDS instance and stores its data as an attribute on the
new deployed service.
"""
import re
import time
from infrastructure.models import CustomField, Environment
from resourcehandlers.aws.models import AWSHandler
from common.methods import set_progress
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

def get_or_create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='aws_rh_id',
        defaults={
            "label": 'AWS RH ID',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint'
        }
    )

    CustomField.objects.get_or_create(
        name='db_identifier',
        defaults={
            "label": 'AWS database identifier',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint'
        }
    )
    
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
        name='db_availability_zone',
        defaults={
            "label": 'Availability Zone',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint'
        }
    )

    CustomField.objects.get_or_create(
        name='db_subnet_group',
        defaults={
            "label": 'Subnet group',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint'
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
        name='db_publicly_accessible',
        defaults={
            "label": 'Publicly Accessible',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint'
        }
    )
    
    CustomField.objects.get_or_create(
        name='db_engine',
        defaults={
            "label": 'Engine',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint'
        }
    )
    
    CustomField.objects.get_or_create(
        name='db_status',
        defaults={
            "label": 'Status',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint'
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
    
    CustomField.objects.get_or_create(
        name='db_cluster_identifier',
        defaults={
            "label": 'DBClusterIdentifier',
            "type": 'STR',
            "description": 'Used by the AWS Databases blueprint'
        }
    )
    

def get_boto3_service_client(env, service_name="rds"):
    """
    Return boto connection to the RDS in the specified environment's region.
    """
    # get aws resource handler object
    rh = env.resource_handler.cast()

    # get aws wrapper object
    wrapper = rh.get_api_wrapper()

    # get aws client object
    client = wrapper.get_boto3_client(service_name, rh.serviceaccount, rh.servicepasswd, env.aws_region)
    
    return client

def boto_instance_to_dict(boto_instance, env, rds_client):
    """
    Create a pared-down representation of an RDS instance from the full boto dictionary.
    """

    instance = {
        'name': boto_instance['DBInstanceIdentifier'],
        'aws_region': env.aws_region,
        'aws_rh_id': env.resource_handler.cast().id,
        'db_identifier': boto_instance['DBInstanceIdentifier'],
        'db_engine': boto_instance['Engine'],
        'db_status': boto_instance['DBInstanceStatus'],
        'db_username': boto_instance['MasterUsername'],
        'db_publicly_accessible': boto_instance['PubliclyAccessible'],
        'db_availability_zone': boto_instance.get("AvailabilityZone", ""),
        'db_cluster_identifier': boto_instance.get("DBClusterIdentifier", "")
    }
    
    # get subnet object
    subnet_group = boto_instance.get("DBSubnetGroup", {})

    # Endpoint may not be returned if networking is not set up yet
    endpoint = boto_instance.get('Endpoint', {})
    
    if not endpoint:
        time.sleep(10)
        
        # fetch RDS DB instance
        rds_rsp = rds_client.describe_db_instances(DBInstanceIdentifier=boto_instance['DBInstanceIdentifier'], 
                                    Filters=[{'Name':'engine','Values':[boto_instance['Engine']]}])['DBInstances']
        if rds_rsp:
            endpoint = rds_rsp[0].get('Endpoint', {})

    instance.update({'db_endpoint_address': endpoint.get('Address'), 
        'db_endpoint_port': endpoint.get('Port'), 
        'db_subnet_group': subnet_group.get("DBSubnetGroupName"),
        'db_subnets': [xx['SubnetIdentifier'] for xx in subnet_group.get("Subnets", [])]})
    
    logger.info(f'RDS instance {instance} created successfully.')

    return instance

def sort_dropdown_options(data, placeholder=None, is_reverse=False):
    """
    Sort dropdown options 
    """
    # remove duplicate option from list
    data = list(set(data))

    # sort options
    sorted_options = sorted(data, key=lambda tup: tup[1].lower(), reverse=is_reverse)
    
    if placeholder is not None:
        sorted_options.insert(0, placeholder)
    
    return {'options': sorted_options, 'override': True}
    
    
def generate_options_for_aws_region(profile=None, **kwargs):
    """
    Generate AWS region options
    """
    envs_this_user_can_view = Environment.objects_for_profile(profile)
    
    # get all aws handler
    aws_handlers = AWSHandler.objects.all()
    
    # get all aws region
    aws_envs = envs_this_user_can_view.filter(resource_handler_id__in=aws_handlers)
    
    if not aws_envs:
        return [("", "-----Select Environment-----")]
    
    client = get_boto3_service_client(aws_envs[0])
    
    # fetch all rds supported regions
    rds_support_regions = [region['RegionName'] for region in client.describe_source_regions()['SourceRegions']]
    options = []
    
    for env in aws_envs:
        if env.aws_region not in rds_support_regions:
            continue
        
        options.append((env.id, env.name))
    
    return sort_dropdown_options(options, ("", "-----Select Environment-----"))


def generate_options_for_db_engine(control_value=None, **kwargs):
    """
    Generate RDS Databse Engine options
    Dependecy: RDS Region
    """
    options = []
    
    if control_value is None or control_value == "":
        options.append(("", "-----First, Select Environment-----"))
        return options

    options = [
        (f'aurora-mysql/{control_value}', 'Aurora MySQL'),
        (f'aurora-postgresql/{control_value}', 'Aurora PostgreSQL'),
        (f'mariadb/{control_value}', 'MariaDB'),
        (f'mysql/{control_value}', 'MySQL'),
        (f'postgres/{control_value}', 'PostgreSQL'),
        (f'oracle-se2/{control_value}', 'Oracle Database Standard Edition Two'),
        (f'oracle-ee/{control_value}', 'Oracle Database Enterprise Edition'),
        (f'sqlserver-ee/{control_value}', 'Microsoft SQL Server Enterprise Edition'),
        (f'sqlserver-se/{control_value}', 'Microsoft SQL Server Standard Edition'),
        (f'sqlserver-ex/{control_value}', 'Microsoft SQL Server Express Edition'),
        (f'sqlserver-web/{control_value}', 'Microsoft SQL Server Web Edition'),
    ]

    return sort_dropdown_options(options, ("", "-----Select Database Engine-----"))

def generate_options_for_db_engine_version(control_value=None, **kwargs):
    """
    Generate RDS Databse Engine version options
    Dependecy: RDS Database Engine
    """
    options = []
    
    if control_value is None or control_value == "":
        options.append(("", "-----First, Select Database Engine-----"))
        return options
    
    control_value = control_value.split("/")
    env = Environment.objects.get(id=control_value[1])

    # get rds boto3 client
    client = get_boto3_service_client(env)
    
    version_rgx = '^\d(\.\d)*$'
    filters=[{'Name':'status','Values':['available']},{'Name':'engine-mode','Values':['provisioned']}]
    
    for engine in client.describe_db_engine_versions(Engine=control_value[0], IncludeAll=False, Filters=filters)['DBEngineVersions']:
        option_label = engine['DBEngineVersionDescription']
        
        if re.match(version_rgx, engine['EngineVersion']) and engine['EngineVersion'] not in engine['DBEngineVersionDescription']:
            option_label = "{0} : {1}".format(engine['DBEngineVersionDescription'], engine['EngineVersion'])
            
        options.append(("{0}/{1}/{2}".format(engine['EngineVersion'], env.id, control_value[0]), option_label))
    
    return sort_dropdown_options(options, ("", "-----Select Engine Version-----"), True)
    
def generate_options_for_instance_class(control_value=None, **kwargs):
    """
    Generate RDS Databse Engine Version instance class options
    Dependecy: RDS Database Engine Version
    """
    options = []
    
    if control_value is None or control_value == "":
        options.append(("", "-----First, Select Engine Version-----"))
        return options
    
    control_value = control_value.split("/")
    env = Environment.objects.get(id=control_value[1])

    # get rds boto3 client
    client = get_boto3_service_client(env)
    
    ins_cls_dict = {'xlarge': {'cpu': 4, 'storage': 32}, '2xlarge': {'cpu': 8, 'storage': 64}, '4xlarge': {'cpu': 16, 'storage': 128}, 
                    '8xlarge':{'cpu': 32, 'storage': 256}, '16xlarge': {'cpu': 64, 'storage': 512}, 'large': {'cpu': 2, 'storage': 16},
                    'small': {'cpu': 2, 'storage': 2}, 'medium': {'cpu': 2, 'storage':4}
                    }
    
    # fetch all db engine version instance classes
    instance_klasss = client.describe_orderable_db_instance_options(Engine=control_value[2], Vpc=True, 
                                    EngineVersion=control_value[0])['OrderableDBInstanceOptions']
    
    for instance_klass in instance_klasss:
        storage = None
        cpu = None
        st_dict = ins_cls_dict.get(instance_klass['DBInstanceClass'].split(".")[-1], None)

        if "MaxStorageSize" in instance_klass and st_dict is not None:  
            if instance_klass['MinStorageSize']  <= st_dict['storage'] <= instance_klass['MaxStorageSize']:
                storage = st_dict['storage']
                cpu = st_dict['cpu']
            else:
                storage = instance_klass['MinStorageSize']
                cpu = int(storage)//8 if int(storage)//8 > 1 else 2
                
        elif st_dict is not None:
            storage = st_dict['storage']
            cpu = st_dict['cpu']

        if cpu is None:
            continue

        key = "{0}$?{1}$?{2}$?{3}".format(instance_klass['DBInstanceClass'], storage, instance_klass['LicenseModel'], instance_klass['StorageType'])
        name = "{0} ({1} GiB RAM,   {2} vCPUs, {3} Storage)".format(instance_klass['DBInstanceClass'],storage, cpu, 
                                                    instance_klass['StorageType'].capitalize())
        options.append((key, name))
    
    return sort_dropdown_options(options, ("", "-----Select Instance Class-----"), True)


def find_or_create_rds_subnet_group(rds_client, env):
    """
    Find or create rds subnet group
    """
    subnet_group = None
    
    for sb_gp in rds_client.describe_db_subnet_groups()['DBSubnetGroups']:
        subnet_group = sb_gp['DBSubnetGroupName']
        break
    
    if subnet_group is None:
        # get ec2 boto3 client object
        ec2_client = get_boto3_service_client(env, 'ec2')

        # fetch all ec2 region subnets
        subnets = ec2_client.describe_subnets()['Subnets']

        if not subnets:
            raise RuntimeError(f"Subnet does not exists for EC2 region({env.aws_region})")

        vpc_id = subnets[0]['VpcId']

        try:
            # create subnet group
            sub_resp = rds_client.create_db_subnet_group(
                DBSubnetGroupName=f'default-{vpc_id}',
                DBSubnetGroupDescription='Created subnet group for RDS DB instance',
                SubnetIds= [xx['SubnetId'] for xx in subnets if xx['VpcId'] == vpc_id]
            )
        except Exception as err:
            raise RuntimeError(err)
        else:
            subnet_group = sub_resp['DBSubnetGroup']['DBSubnetGroupName']
            time.sleep(10)

    return subnet_group

def create_rds_db_cluster(client, cluster_identifier, **cluster_kwargs):
    """
    Create RDS DB instance cluster
    """
    cluster_kwargs['DBClusterIdentifier'] = cluster_identifier
    
    set_progress(f'Started provision of rds cluster: {cluster_identifier}')
    logger.info('Started provision of rds cluster'.format(cluster_kwargs))
    
    try:
        # create database cluster
        cluster_rsp = client.create_db_cluster(**cluster_kwargs)['DBCluster']
    except Exception as err:
        if 'DBClusterAlreadyExistsFault' not in str(err):
            raise RuntimeError(err)
    
    while cluster_rsp['Status'] != "available":
        time.sleep(20)
        
        # fetch rds db cluster
        cluster_rsp = client.describe_db_clusters(DBClusterIdentifier=cluster_identifier,
                                        Filters=[{'Name':'engine','Values':[cluster_kwargs['Engine']]}])['DBClusters'][0]
    return cluster_identifier

def run(resource, logger=None, **kwargs):
    set_progress('Creating AWS RDS instance...')
    logger.info('Creating AWS RDS instance...')
    
    # get or create custom fields
    get_or_create_custom_fields_as_needed()
    
    # AWS requires DB Name to have a certain format (only alphanumeric). To
    # have CB properly validate user input on this parameter, an admin should go
    # to the action's detail page, edit the 'DB Name' Action Input and set a
    # "Regex constraint" value of "^[a-zA-Z]\w+$".
    db_name = '{{ db_name }}'
    db_username = '{{ db_username }}'
    db_password = '{{ db_password }}'
    db_identifier = '{{ db_identifier }}'
    instance_class_obj = '{{ instance_class }}'.split("$?")
    engine = '{{ db_engine }}'.split("/")[0]
    db_engine_version = '{{ db_engine_version }}'.split("/")[0]
    license_model = instance_class_obj[2]
    instance_class = instance_class_obj[0]
    allocated_storage = int(instance_class_obj[1])

    env = Environment.objects.get(id='{{ aws_region }}')
    
    set_progress('Connecting to AWS RDS in region {0}.'.format(env.aws_region))
    logger.info('Connecting to AWS RDS in region {0}.'.format(env.aws_region))
        
    # get boto client object
    client = get_boto3_service_client(env)
    
    storage_type = instance_class_obj[3]
    
    rds_payload = dict(
        DBInstanceIdentifier=db_identifier,
        DBInstanceClass=instance_class,
        StorageType=storage_type,
        AutoMinorVersionUpgrade=False,
        CopyTagsToSnapshot=True,
        LicenseModel = license_model
    )
    
    # get or create subnet group
    subnet_group = find_or_create_rds_subnet_group(client, env) 
    common_kwargs = dict(Engine=engine, EngineVersion=db_engine_version,MasterUserPassword=db_password, BackupRetentionPeriod=7, StorageEncrypted=True,
                                    MasterUsername=db_username, DeletionProtection=False, DBSubnetGroupName=subnet_group)
    if storage_type == "aurora":
        rds_payload['Engine'] = engine
        rds_payload['EngineVersion'] = db_engine_version
        rds_payload['DBSubnetGroupName'] = subnet_group

        # create rds db cluster
        rds_payload['DBClusterIdentifier'] = create_rds_db_cluster(client, "{0}-c".format(db_identifier), **common_kwargs)
    else:    
        rds_payload['AllocatedStorage'] = allocated_storage
        
        if 'sqlserver' not in  common_kwargs['Engine']: # Microsoft SQL server does not support DBName field
            rds_payload['DBName'] = db_name
        
        if storage_type == 'io1':
            rds_payload['Iops'] = 1000
        
        if common_kwargs['Engine'] in ['sqlserver-ex']:
            del common_kwargs['StorageEncrypted']
            
        rds_payload.update(common_kwargs)
    
    set_progress(f'Started provision of rds instance: {db_identifier}')
    logger.info('Started provision of rds instance:\n{0}'.format(rds_payload))

    try:
        # create rds db instance
        rds_response = client.create_db_instance(**rds_payload)
    except Exception as err:
        if 'DBInstanceAlreadyExists' in str(err):
            return "FAILURE", "Database already exists", "DB instance {} exists already".format(db_identifier)
        raise
    
    # It takes awhile for the DB to be created and backed up.
    waiter = client.get_waiter('db_instance_available')
    waiter.config.max_attempts = 100  # default is 40 but oracle takes more time.
    waiter.wait(DBInstanceIdentifier=db_identifier)
    
    logger.info(f"RDS instance response {rds_response}")
    
    # convert boto model into cb rds dict
    rds_instance = boto_instance_to_dict(rds_response['DBInstance'], env, client)

    for key, value in rds_instance.items():
        setattr(resource, key, value) # set custom field value

    resource.name = db_identifier
    resource.save()

    set_progress(f'RDS instance {db_identifier} created successfully.')
    
    return 'SUCCESS', f'RDS instance {db_identifier} created successfully.', ''