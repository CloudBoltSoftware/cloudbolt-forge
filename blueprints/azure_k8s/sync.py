"""
Discover Azure Resource groups and clusters
Return Azure Resource groups and clusters identified by sku, handler_id and
location
"""
from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from datetime import datetime

RESOURCE_IDENTIFIER = 'output_resource_0_id'


def discover_resources(**kwargs):
    discovered_clusters = []
    for rh in AzureARMHandler.objects.all():
        set_progress(
            'Connecting to Azure Resource Group for handler: {}'.format(rh))
        credentials = ServicePrincipalCredentials(
            client_id=rh.client_id,
            secret=rh.secret,
            tenant=rh.azure_tenant_id
        )
        resource_client = ResourceManagementClient(credentials,
                                                   rh.serviceaccount)
        container_client = ContainerServiceClient(credentials,
                                                  rh.serviceaccount)

        for rg in list(resource_client.resource_groups.list()):
            for cluster in list(
                    container_client.managed_clusters.list_by_resource_group(
                            resource_group_name=rg.name)):
                set_progress(f'Discovered aks cluster: {cluster.name}')
                discovered_cluster = {
                    'name': f'{cluster.name}',
                    'azure_rh_id': rh.id,
                    'resource_group': rg.name,
                    'azure_location': cluster.location,
                    'dns_prefix': cluster.dns_prefix,
                    'enable_rbac': cluster.enable_rbac,
                    'kubernetes_version': cluster.kubernetes_version,
                    'last_synced': datetime.now(),
                    'synced_from_system': True,
                    'output_resource_0_id': cluster.id,
                    'node_count': cluster.agent_pool_profiles[0].count,
                    'os_disk_size': cluster.agent_pool_profiles[
                        0].os_disk_size_gb,
                    'node_size': cluster.agent_pool_profiles[0].vm_size
                }
                try:
                    discovered_cluster["enable_azure_policy"] = (
                        cluster.addon_profiles.get('azurepolicy').enabled)
                except AttributeError:
                    pass
                try:
                    discovered_cluster["http_application_routing"] = (
                        cluster.addon_profiles.get(
                            'httpApplicationRouting').enabled)
                except AttributeError:
                    pass
                try:
                    discovered_cluster["enable_private_cluster"] = (
                        cluster.api_server_access_profile.enable_private_cluster)
                except AttributeError:
                    pass
                discovered_clusters.append(discovered_cluster)
    return discovered_clusters
