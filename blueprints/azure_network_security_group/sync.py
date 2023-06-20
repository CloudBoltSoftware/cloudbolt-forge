"""
Synchronize Azure network security groups
"""
import azure.mgmt.resource.resources as resources
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.network import NetworkManagementClient
from msrestazure.azure_exceptions import CloudError

from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler


RESOURCE_IDENTIFIER = "azure_network_security_group"


def get_tenant_id_for_azure(handler):
    '''
        Handling Azure RH table changes for older and newer versions (> 9.4.5)
    '''
    if hasattr(handler,"azure_tenant_id"):
        return handler.azure_tenant_id

    return handler.tenant_id


def discover_resources(**kwargs):
    discovered_virtual_nets = []
    for handler in AzureARMHandler.objects.all():
        set_progress(
            "Connecting to Azure networks \
        for handler: {}".format(
                handler
            )
        )
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id, secret=handler.secret, tenant=get_tenant_id_for_azure(handler)
        )
        network_client = NetworkManagementClient(credentials, handler.serviceaccount)

        azure_resources_client = resources.ResourceManagementClient(
            credentials, handler.serviceaccount
        )

        for resource_group in azure_resources_client.resource_groups.list():
            try:
                for security_group in network_client.network_security_groups.list(
                    resource_group_name=resource_group.name
                ):
                    discovered_virtual_nets.append(
                        {
                            "name": "Azure NSG - " + security_group.as_dict()["name"],
                            "azure_network_security_group": security_group.as_dict()[
                                "name"
                            ],
                            "azure_location": security_group.as_dict()["location"],
                            "azure_rh_id": handler.id,
                            "resource_group_name": resource_group.name,
                        }
                    )
            except CloudError as e:
                set_progress("Azure Clouderror: {}".format(e))
                continue

    return discovered_virtual_nets
