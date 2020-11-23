import boto3
from common.methods import set_progress
from resourcehandlers.aws.models import AWSHandler
from botocore.client import ClientError

RESOURCE_IDENTIFIER = 'glacier_vault_name'


def discover_resources(**kwargs):
    discovered_stores = []

    for handler in AWSHandler.objects.all():
        set_progress('Connecting to Amazon Glacier (Cold Storage) for handler: {}'.format(handler))
        try:
            wrapper = handler.get_api_wrapper()
        except Exception as e:
            set_progress(f"Could not get wrapper: {e}")
            continue
        for region in handler.current_regions():
            glacier = boto3.client(
                'glacier',
                region_name=region,
                aws_access_key_id=handler.serviceaccount,
                aws_secret_access_key=handler.servicepasswd
            )
            try:
                vaults = glacier.list_vaults()['VaultList']

                for vault in vaults:
                    discovered_stores.append({
                        'name': vault['VaultName'],
                        'glacier_vault_name': vault['VaultName'],
                        'aws_region': region,
                        'aws_rh_id': handler.id
                    })

                marker = glacier.list_vaults().get('Marker', None)

                '''
                glacier.list_vaults()
                returns up to 10 items.
                If there are more vaults to list, the response marker field contains the vault Amazon Resource Name (ARN)
                at which to continue the list with a new List Vaults request
                '''
                while marker:
                    vaults = glacier.list_vaults(marker=marker)['VaultList']
                    for vault in vaults:
                        discovered_stores.append({
                            'name': vault['VaultName'],
                            'glacier_vault_name': vault['VaultName'],
                            'aws_region': region,
                            'aws_rh_id': handler.id,
                        })

                    marker = glacier.list_vaults(marker=marker).get('Marker', None)

            except ClientError as e:
                set_progress('AWS ClientError: {}'.format(e))
                continue

    return discovered_stores
