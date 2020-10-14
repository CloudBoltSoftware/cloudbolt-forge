import boto3
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from infrastructure.models import CustomField

RESOURCE_IDENTIFIER = 'file_system_id'


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


def discover_resources(**kwargs):
    # Just in case the custom fields do not exist.
    create_custom_fields_as_needed()

    discovered_file_systems = []

    for handler in AWSHandler.objects.all():
        set_progress('Connecting to Amazon FXs for handler: {}'.format(handler))

        for region in handler.current_regions():

            fsx = boto3.client(
                'fsx',
                region_name=region,
                aws_access_key_id=handler.serviceaccount,
                aws_secret_access_key=handler.servicepasswd,
            )
            try:
                file_systems = fsx.describe_file_systems().get('FileSystems')
                for file_system in file_systems:
                    discovered_file_systems.append(
                        {
                            'name': file_system.get('FileSystemId'),
                            'file_system_id': file_system.get('FileSystemId'),
                            'aws_rh_id': handler.id,
                            'aws_region': region,
                            'subnet_ids': file_system.get('SubnetIds'),
                            'storage_capacity': int(file_system.get('StorageCapacity')),
                            'file_system_type': file_system.get('FileSystemType')
                        }
                    )

            except Exception as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return discovered_file_systems
