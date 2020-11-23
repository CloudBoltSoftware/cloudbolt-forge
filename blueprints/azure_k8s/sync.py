"""
Discover Azure Resource groups and clusters
Return Azure Resource groups and clusters identified by sku, handler_id and location
"""
from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.containerservice.models import ManagedClusterServicePrincipalProfile
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.containerservice.models import ManagedCluster
from azure.mgmt.resource.resources.models import ResourceGroup


RESOURCE_IDENTIFIER = 'aks_cluster_name'

def discover_resources(**kwargs):

    discovered_resource_groups = []
    for handler in AzureARMHandler.objects.all():
        set_progress('Connecting to Azure Resource Groups \
        for handler: {}'.format(handler))
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=handler.tenant_id
        )
        azure_client = ResourceManagementClient(credentials, handler.serviceaccount)
        for rg in azure_client.resource_groups.list():
            discovered_resource_groups.append({
                'name': rg.name,
                'azure_rh_id': handler.id,
                'resource_group_name': rg.name
            })
    return discovered_resource_groups
