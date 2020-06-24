"""
Delete an Azure network security group.
"""
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.network import NetworkManagementClient
from msrestazure.azure_exceptions import CloudError

from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler


def run(job, **kwargs):
    resource = kwargs.pop("resources").first()

    azure_network_security_group = resource.attributes.get(
        field__name="azure_network_security_group"
    ).value
    resource_group = resource.attributes.get(field__name="resource_group_name").value
    rh_id = resource.attributes.get(field__name="azure_rh_id").value
    rh = AzureARMHandler.objects.get(id=rh_id)

    set_progress("Connecting To Azure networking...")
    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id, secret=rh.secret, tenant=rh.tenant_id
    )

    network_client = NetworkManagementClient(credentials, rh.serviceaccount)
    set_progress("Connection to Azure networking established")

    set_progress(
        "Deleting network security group %s..." % (azure_network_security_group)
    )

    try:
        network_client.network_security_groups.delete(
            resource_group_name=resource_group,
            network_security_group_name=azure_network_security_group,
        )
    except CloudError as e:
        set_progress("Azure Clouderror: {}".format(e))
        return "FAILURE", "Network security group could not be deleted", ""

    return "SUCCESS", "The network security group has been succesfully deleted", ""
