from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
import azure.mgmt.storage as storage
from resourcehandlers.azure_arm.models import ARMResourceGroup, AzureARMHandler
from resources.models import ResourceType, Resource
from accounts.models import Group
from servicecatalog.models import ServiceBlueprint

RESOURCE_IDENTIFIER = 'azure_container_id'


def discover_resources(**kwargs):
    containers = []
    resource_type = ResourceType.objects.get(name__iexact='storage')
    blue_print = ServiceBlueprint.objects.get(name__iexact='azure storage container')

    for handler in AzureARMHandler.objects.all():
        set_progress('Connecting to Azure for handler: {}'.format(handler))

        # getting all storage accounts
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=handler.tenant_id,
        )
        client = storage.StorageManagementClient(credentials, handler.serviceaccount)

        accounts = client.storage_accounts.list()
        for resource_group in ARMResourceGroup.objects.all():
            for account in accounts:
                for container in client.blob_containers.list(resource_group_name=resource_group.name, account_name=account.name).value:
                    try:
                        storage_account = container.as_dict().get('id').split('/')[-5]
                        resource, _ = Resource.objects.get_or_create(
                            name=container.name,
                            defaults={
                                'blueprint': blue_print,
                                'resource_type': resource_type,
                                'group': Group.objects.get(name__icontains='unassigned'),
                                'parent_resource': Resource.objects.filter(name__icontains=account.name).first(),
                            })
                        resource_g_name = resource_group.name

                        # Get and save account key
                        res = client.storage_accounts.list_keys(resource_g_name, storage_account)
                        keys = res.keys
                        resource.lifecycle = "ACTIVE"
                        resource.azure_rh_id = handler.id
                        resource.azure_container_name = container.name
                        resource.azure_account_key = keys[0].value
                        resource.resource_group_name = resource_g_name
                        resource.azure_account_name = account.name
                        resource.save()

                    except Exception as e:
                        set_progress('Azure ClientError: {}'.format(e))
                        continue

    return containers
