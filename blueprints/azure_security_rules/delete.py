"""
Delete an Azure network security rule.
"""
from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from msrestazure.azure_exceptions import CloudError
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.network import NetworkManagementClient

def run(job, **kwargs):
    resource = kwargs.pop('resources').first()

    azure_network_security_group = resource.attributes.get(field__name='azure_network_security_group_name').value
    azure_security_rule_name = resource.attributes.get(field__name='azure_security_rule_name').value
    resource_group = resource.attributes.get(
        field__name='resource_group_name').value
    rh_id = resource.attributes.get(field__name='azure_rh_id').value
    rh = AzureARMHandler.objects.get(id=rh_id)

    set_progress("Connecting To Azure networking...")
    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id,
        secret=rh.secret,
        tenant=rh.tenant_id
    )

    network_client = NetworkManagementClient(credentials, rh.serviceaccount)
    set_progress("Connection to Azure networking established")

    set_progress("Deleting network security rule %s..." % (azure_security_rule_name))

    try:
        network_client.security_rules.delete(resource_group_name=resource_group, network_security_group_name=azure_network_security_group, security_rule_name=azure_security_rule_name)
    except CloudError as e:
        return "FAILURE", "Network security group could not be deleted", e

    return "SUCCESS", "The network security rule has been succesfully deleted", ""