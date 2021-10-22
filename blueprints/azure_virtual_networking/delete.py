"""
Delete an Azure virtual network.
"""
from common.methods import set_progress
from azure.common.credentials import ServicePrincipalCredentials
from msrestazure.azure_exceptions import CloudError
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.network import NetworkManagementClient

def get_tenant_id_for_azure(handler):
    '''
        Handling Azure RH table changes for older and newer versions (> 9.4.5)
    '''
    if hasattr(handler,"azure_tenant_id"):
        return handler.azure_tenant_id
    return handler.tenant_id
    
def run(job, **kwargs):
    resource = kwargs.pop('resources').first()

    virtual_net_name = resource.attributes.get(field__name='azure_virtual_net_name').value
    resource_group = resource.attributes.get(
        field__name='resource_group_name').value
    rh_id = resource.attributes.get(field__name='azure_rh_id').value
    rh = AzureARMHandler.objects.get(id=rh_id)

    set_progress("Connecting To Azure...")
    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id,
        secret=rh.secret,
        tenant=get_tenant_id_for_azure(rh)
    )

    network_client = NetworkManagementClient(credentials, rh.serviceaccount)
    set_progress("Connection to Azure established")

    set_progress("Deleting virtual network %s..." % (virtual_net_name))

    try:
        network_client.virtual_networks.delete(resource_group_name=resource_group, virtual_network_name=virtual_net_name)
    except CloudError as e:
        set_progress("Azure Clouderror: {}".format(e))
        return "FAILURE", "Virtual network could not be deleted", ""

    return "SUCCESS", "The virtual net has been succesfully deleted", ""