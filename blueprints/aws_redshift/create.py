from infrastructure.models import Environment
from infrastructure.models import CustomField

import boto3


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='aws_rh_id', defaults={
            'label': 'AWS RH ID', 'type': 'STR',
            'description': 'Used by the AWS blueprints'
        }
    )
    CustomField.objects.get_or_create(
        name='env_id', defaults={
            'label': 'Env ID', 'type': 'STR'
        }
    )
    CustomField.objects.get_or_create(
        name='name', defaults={
            'label': 'AWS Redshift', 'type': 'STR',
            'description': 'Name of the AWS Redshift cluster'
        }
    )
    CustomField.objects.get_or_create(
        name='cluster_name', defaults={
            'label': 'AWS Redshift cluster_name', 'type': 'STR',
            'description': 'Name of the AWS Redshift cluster'
        }
    )
    CustomField.objects.get_or_create(
        name='node_type', defaults={
            'label': 'Redshift cluster Node Type', 'type': 'STR',
            'description': 'The node type to be provisioned for the cluster'
        }
    )
    CustomField.objects.get_or_create(
        name='master_username', defaults={
            'label': 'Redshift cluster Master Username', 'type': 'STR',
            'description': 'The user name associated with the master user account for the cluster that is being created.'
        }
    )
    CustomField.objects.get_or_create(
        name='master_password', defaults={
            'label': 'Redshift cluster MasterUserPassword', 'type': 'PWD',
            'description': 'The password associated with the master user account for the cluster that is being created.'
        }
    )
    CustomField.objects.get_or_create(
        name='cluster_type', defaults={
            'label': 'Redshift cluster Type', 'type': 'STR',
            'description': 'The type of the cluster.'
        }
    )


def connect_to_redshift(env):
    """
    Return boto connection to the redshift in the specified environment's region.
    """
    rh = env.resource_handler.cast()
    return (boto3.client(
        'redshift',
        region_name=env.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd), rh.id)


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").values("id", "name")
    options = [(env['id'], env['name']) for env in envs]
    return options


def generate_options_for_node_type(**kwargs):
    return [
        ('dc2.large', 'NodeType - dc2.large'),
        ('ds2.xlarge', 'NodeType - ds2.xlarge'),
        ('ds2.8xlarge', 'NodeType - ds2.8xlarge'),
        ('dc1.large', 'NodeType - dc1.large'),
        ('dc1.8xlarge', 'NodeType - dc1.8xlarge'),
        ('dc2.8xlarge', 'NodeType - dc2.8xlarge'),
    ]


def generate_options_for_cluster_type(**kwargs):
    return [('single-node', 'Single Node'), ('multi-node', 'Multi Node')]


def run(resource, *args, **kwargs):
    create_custom_fields_as_needed()
    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    DBName = "{{ DBName }}"
    ClusterIdentifier = "{{ ClusterIdentifier }}"
    NodeType = "{{ node_type }}"
    NumberOfNodes = "{{ number_of_nodes }}"
    ClusterType = "{{ cluster_type }}"
    MasterUsername = "{{ master_username }}"
    MasterUserPassword = "{{ master_password }}"

    connection, aws_rh_id = connect_to_redshift(env)

    try:
        if ClusterType == 'multi-node':
            connection.create_cluster(
                ClusterIdentifier=ClusterIdentifier,
                NodeType=NodeType,
                DBName=DBName,
                MasterUsername=MasterUsername.lower(),
                MasterUserPassword=MasterUserPassword,
                ClusterType=ClusterType,
                NumberOfNodes=int(NumberOfNodes))
        else:
            connection.create_cluster(
                ClusterIdentifier=ClusterIdentifier,
                NodeType=NodeType,
                DBName=DBName,
                MasterUsername=MasterUsername.lower(),
                MasterUserPassword=MasterUserPassword,
                ClusterType=ClusterType)

    except Exception as error:
        return "FAILURE", "", f"{error}"

    resource.name = ClusterIdentifier
    resource.aws_rh_id = aws_rh_id
    resource.env_id = env_id
    resource.node_type = NodeType
    resource.master_username = MasterUsername.lower()
    resource.master_password = MasterUserPassword
    resource.cluster_type = ClusterType
    resource.cluster_name = ClusterIdentifier
    resource.save()

    return "SUCCESS", "", ""
