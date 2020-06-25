"""
Discover Azure storage queues
"""
import azure.mgmt.storage as storage
import azure.mgmt.resource.resources as resources
from azure.common.credentials import ServicePrincipalCredentials
from azure.storage.queue import QueueService
from msrestazure.azure_exceptions import CloudError

from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler


RESOURCE_IDENTIFIER = "azure_queue_name"


def discover_resources(**kwargs):
    discovered_azure_queues = []
    for handler in AzureARMHandler.objects.all():
        set_progress(
            "Connecting to Azure sql \
        DB for handler: {}".format(
                handler
            )
        )
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id, secret=handler.secret, tenant=handler.tenant_id
        )
        azure_client = storage.StorageManagementClient(
            credentials, handler.serviceaccount
        )
        azure_resources_client = resources.ResourceManagementClient(
            credentials, handler.serviceaccount
        )

        for resource_group in azure_resources_client.resource_groups.list():
            try:
                for st in (
                    azure_client.storage_accounts.list_by_resource_group(
                        resource_group.name
                    )
                    ._get_next()
                    .json()["value"]
                ):
                    try:
                        res = azure_client.storage_accounts.list_keys(
                            resource_group.name, st["name"]
                        )
                        keys = res.keys
                        for queue in QueueService(
                            account_name=st["name"], account_key=keys[1].value
                        ).list_queues():
                            discovered_azure_queues.append(
                                {
                                    "name": queue.name,
                                    "azure_queue_name": "Azure queues - " + queue.name,
                                    "resource_group_name": resource_group.name,
                                    "azure_rh_id": handler.id,
                                    "azure_storage_account_name": st["name"],
                                    "azure_account_key": keys[0].value,
                                    "azure_account_key_fallback": keys[1].value,
                                }
                            )
                    except:  # noqa: E722
                        continue
            except CloudError as e:
                set_progress("Azure CloudError: {}".format(e))
                continue

    return discovered_azure_queues
