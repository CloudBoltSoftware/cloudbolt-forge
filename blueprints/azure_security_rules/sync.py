"""
Synchronize Azure network security rules
"""
from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.network import NetworkManagementClient
from msrestazure.azure_exceptions import CloudError
import azure.mgmt.resource.resources as resources


RESOURCE_IDENTIFIER = 'azure_network_security_group_name'

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
        set_progress('Connecting to Azure networks \
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
                for security_group in network_client.network_security_groups.list(resource_group_name=resource_group.name):
                    for security_rule in network_client.security_rules.list(resource_group_name=resource_group.name, network_security_group_name=security_group.as_dict()['name']):
                        discovered_virtual_nets.append(
                                {
                                'name': 'Azure Security rule - ' + security_group.as_dict()['name'] + " " + security_rule.as_dict()['direction'],
                                'azure_network_security_group_name': security_group.as_dict()['name'],
                                'azure_location': security_group.as_dict()['location'],
                                'azure_rh_id': handler.id,
                                'resource_group_name': resource_group.name,
                                'azure_security_rule_protocol': security_rule.as_dict()['protocol'],
                                'azure_security_rule_access': security_rule.as_dict()['access'],
                                'azure_security_rule_direction': security_rule.as_dict()['direction'],
                                'azure_security_rule_name': security_rule.as_dict()['name'],
                                }
                            )
            except CloudError as e:
                set_progress('Azure Clouderror: {}'.format(e))
                continue

    return discovered_virtual_nets