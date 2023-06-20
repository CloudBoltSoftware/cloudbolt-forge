from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment

import boto3
import time
from ast import literal_eval as make_tuple


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
        name='file_system_type', defaults={
            'label': 'FileSystemType', 'type': 'STR',
            'description': 'The type of file system.'
        }
    )
    CustomField.objects.get_or_create(
        name='file_system_id', defaults={
            'label': 'FileSystemId', 'type': 'STR',
            'description': 'The ID of the file system created.'
        }
    )
    CustomField.objects.get_or_create(
        name='storage_capacity', defaults={
            'label': 'StorageCapacity', 'type': 'INT',
            'description': " The storage capacity of the file system."
                           "For Windows file systems, the storage capacity has a minimum of 300 GiB,"
                           "and a maximum of 65,536 GiB. For Lustre file systems, the storage capacity has a minimum "
                           "of 3,600 GiB. Storage capacity is provisioned in increments of 3,600 GiB. "
        }
    )
    CustomField.objects.get_or_create(
        name='subnet_ids', defaults={
            'label': 'SubnetIds', 'type': 'STR',
            'description': "A list of IDs for the subnets that the file system will be accessible from. File systems "
                           "support only one subnet. The file server is also launched in that subnet's Availability "
                           "Zone. "
        }
    )


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Amazon Web Services").values("id", "name")
    options = [(env['id'], env['name']) for env in envs]
    return options


def generate_options_for_file_system_type(**kwargs):
    return ['LUSTRE', 'WINDOWS']

def generate_options_for_subnet_ids(control_value=None, **kwargs):
    if not control_value:
        return []
    env = Environment.objects.get(id=control_value)
    rh = env.resource_handler.cast()

    ec2 = boto3.client('ec2', region_name=env.aws_region,
                       aws_access_key_id=rh.serviceaccount,
                       aws_secret_access_key=rh.servicepasswd)
    subnets = ec2.describe_subnets().get('Subnets')

    result = [(subnet.get('SubnetId') +','+ control_value,  subnet.get('SubnetId')) for subnet in subnets]

    return result


def generate_options_for_active_directory_id(control_value=None, **kwargs):
    if not control_value:
        return []
    control_value = control_value.split(',')
    env = Environment.objects.get(id=control_value[1])
    rh = env.resource_handler.cast()

    client = boto3.client('ds', region_name=env.aws_region,
                          aws_access_key_id=rh.serviceaccount,
                          aws_secret_access_key=rh.servicepasswd)

    directories = client.describe_directories()

    result = []
    for directory in directories.get('DirectoryDescriptions'):
        if control_value[0] in directory.get('VpcSettings').get('SubnetIds'):
            result.append((directory.get('DirectoryId'), directory.get('DirectoryId')))

    return result


def run(resource, logger=None, **kwargs):
    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()

    file_system_type = "{{ file_system_type }}"
    storage_capacity = "{{ storage_capacity }}"
    subnet_ids = "{{ subnet_ids }}"
    subnet_ids = subnet_ids.split(',')
    # Configuration for Microsoft Windows file system.
    ActiveDirectoryId = "{{ active_directory_id }}"  # Optional
    ThroughputCapacity = "{{ ThroughputCapacity }}"
    DailyAutomaticBackupStartTime = "{{ DailyAutomaticBackupStartTime }}"  # Optional
    AutomaticBackupRetentionDays = "{{ AutomaticBackupRetentionDays }}"  # Optional

    set_progress(f"Types AD: {ActiveDirectoryId}, ThroughputCapacity {ThroughputCapacity},"
                 f" DailyAutomaticBackupStartTime {DailyAutomaticBackupStartTime}, AutomaticBackupRetentionDays"
                 f" {AutomaticBackupRetentionDays}")

    set_progress(f"Region is {env.aws_region}")
    fsx = boto3.client(
        'fsx',
        region_name=env.aws_region,
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd,
    )

    set_progress(f"Creating file system...")

    try:
        configurations = {}

        if file_system_type == 'WINDOWS':
            set_progress(f"File system is is {file_system_type}")
            if ActiveDirectoryId != "":
                configurations['ActiveDirectoryId'] = ActiveDirectoryId
            if ThroughputCapacity:
                configurations['ThroughputCapacity'] = int(ThroughputCapacity)

            if DailyAutomaticBackupStartTime != "":
                configurations['DailyAutomaticBackupStartTime'] = DailyAutomaticBackupStartTime

            if AutomaticBackupRetentionDays:
                configurations['AutomaticBackupRetentionDays'] = int(AutomaticBackupRetentionDays)

            res = fsx.create_file_system(
                FileSystemType=file_system_type,
                StorageCapacity=int(storage_capacity),
                SubnetIds=[subnet_ids[0]],
                WindowsConfiguration=configurations)
        else:
            res = fsx.create_file_system(
                FileSystemType=file_system_type,
                StorageCapacity=int(storage_capacity),
                SubnetIds=[subnet_ids[0]])

    except Exception as error:
        return "FAILURE", "", f"{error}"

    file_system_id = res.get('FileSystem').get('FileSystemId')

    # Wait for the file system to be created
    def get_lifecycle():
        _res = fsx.describe_file_systems(FileSystemIds=[file_system_id])

        lifecycle = _res.get('FileSystems')[0].get('Lifecycle')
        return lifecycle

    lifecycle = get_lifecycle()
    while lifecycle == 'CREATING':
        # Sleep for 1 minute
        set_progress(f"File System Status: {lifecycle}")
        time.sleep(60)
        lifecycle = get_lifecycle()

    # At this point, the lifecycle is either AVAILABLE or FAILED
    if lifecycle == "AVAILABLE":
        create_custom_fields_as_needed()
        resource.name = file_system_id
        resource.file_system_id = file_system_id
        resource.aws_rh_id = rh.id
        resource.aws_region = env.aws_region
        resource.subnet_ids = [subnet_ids[0]]
        resource.storage_capacity = int(storage_capacity)
        resource.file_system_type = file_system_type

        resource.save()

    else:
        return "FAILURE", "Couldn't create the file system."

    return "SUCCESS", "", ""