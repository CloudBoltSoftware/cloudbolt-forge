from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.resource import ResourceManagementClient
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource.resources.models import ResourceGroup
from infrastructure.models import CustomField, Environment
from common.methods import set_progress
from msrestazure.azure_exceptions import CloudError

def run(job,**kwargs):
    """
    Delete cluster resources and resource group from Azure, and CB
    """
    resource = kwargs.pop('resources').first()

    resource_group = resource.attributes.get(field__name='resource_group_name').value
    cluster_name = resource.attributes.get(field__name='aks_cluster_name').value
    if not cluster_name:
        return "WARNING", "No cluster associated with this resource"

    env_id = resource.aks_cluster_env
    try:
        environment = Environment.objects.get(id=env_id)
    except Environment.DoesNotExist:
        return ("FAILURE",
                "The environment used to create this cluster no longer exists",
                "")
    rh = environment.resource_handler.cast()

    set_progress("Connecting To Azure Management Service...")
    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id,
        secret=rh.secret,
        tenant=rh.tenant_id
    )

    client = ResourceManagementClient(credentials, rh.serviceaccount)

    try:
        client.managed_clusters.delete(resource_group, cluster_name)
        set_progress("Deleting cluster {}...".format(cluster_name))
    except CloudError as e:
        if e.status_code == 404:
            set_progress('Azure Clouderror {}'.format(cluster_name))
            return "FAILURE", " {} could not be deleted. Does not exist or already deleted".format(cluster_name)
        raise
    set_progress("Delete resource group {}".format(resource_group))
    resource_client.resource_groups.delete(resource_group)

   kubernetes = Kubernetes.objects.get(id=resource.aks_cluster_id)
   kubernetes.delete()

    return "","", ""
