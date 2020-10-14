import boto3
import time

from infrastructure.models import CustomField, Environment


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='aws_rh_id', defaults={
            'label': 'AWS RH ID', 'type': 'STR',
            'description': 'Used by the AWS blueprints'
        }
    )
    CustomField.objects.get_or_create(
        name='aws_region', defaults={
            'label': 'AWS Region', 'type': 'STR',
            'description': 'Used by the AWS blueprints'
        }
    )
    CustomField.objects.get_or_create(
        name='engine', defaults={
            'label': 'AWS Document DB engine', 'type': 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='master_username', defaults={
            'label': 'AWS Document DB Cluster Master Username', 'type': 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='status', defaults={
            'label': 'AWS Document DB Cluster Current status', 'type': 'STR',
        }
    )
    CustomField.objects.get_or_create(
        name='docdb_name', defaults={
            'label': 'AWS Document DB Name', 'type': 'STR',
        }
    )


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").values("id", "name")
    options = [(env['id'], env['name']) for env in envs]
    return options


def run(resource, *args, **kwargs):
    env_id = '{{ env_id }}'
    master_password = "{{ password }}"
    master_username = "{{ username }}"
    cluster_name = "{{ cluster_name }}"

    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    try:
        wrapper = rh.get_api_wrapper()
    except Exception:
        return
    client = wrapper.get_boto3_client(
        'docdb',
        rh.serviceaccount,
        rh.servicepasswd,
        env.aws_region
        )
    try:
        # check if db already exists
        response = client.describe_db_clusters(DBClusterIdentifier=cluster_name)
        status = response.get('DBClusters')[0].get('Status')

        while status == 'deleting':
            time.sleep(2)
            status = client.describe_db_clusters(DBClusterIdentifier=cluster_name).get('DBClusters')[0].get('Status')

    except Exception:
        # Db doesn't exist
        pass

    try:
        response = client.create_db_cluster(
            DBClusterIdentifier=cluster_name,
            Engine="docdb",
            MasterUsername=master_username,
            MasterUserPassword=master_password).get('DBCluster')

    except Exception as error:
        return "FAILURE", "", f"{error}"

    if response:
        resource.name = response['DBClusterIdentifier']
        resource.docdb_name = response['DBClusterIdentifier']
        resource.aws_region = env.aws_region
        resource.aws_rh_id = rh.id
        resource.engine = response['Engine']
        resource.master_username = response['MasterUsername']
        resource.status = 'available'
        resource.save()

    return "SUCCESS", "", ""
