from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.network import NetworkManagementClient
from msrestazure.azure_exceptions import CloudError
import azure.mgmt.resource.resources as resources


RESOURCE_IDENTIFIER = 'azure_virtual_net_name'

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
        set_progress('Connecting to Azure virtual networks \
        for handler: {}'.format(handler))
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=get_tenant_id_for_azure(handler)
        )
        network_client = NetworkManagementClient(credentials, handler.serviceaccount)

        azure_resources_client = resources.ResourceManagementClient(credentials, handler.serviceaccount)

        for resource_group in azure_resources_client.resource_groups.list():
            try:
                for virtual_net in network_client.virtual_networks.list(resource_group_name=resource_group.name):
                    discovered_virtual_nets.append(
                            {
                            'name': virtual_net.as_dict()['name'] + " - " + resource_group.name,
                            'azure_virtual_net_name': virtual_net.as_dict()['name'] + " - " + resource_group.name,
                            'vpn_adress_prefixes': ','.join(virtual_net.as_dict()['address_space']['address_prefixes']),
                            'azure_location': virtual_net.as_dict()['location'],
                            'azure_rh_id': handler.id,
                            'resource_group_name': resource_group.name,
                            }
                        )
            except CloudError as e:
                set_progress('Azure Clouderror: {}'.format(e))
                continue

    return discovered_virtual_nets