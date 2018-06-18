"""
Restart Azure Web App
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.web import WebSiteManagementClient
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.web.models import AppServicePlan, SkuDescription, Site
from resources.models import ResourceType, Resource

def run(job, **kwargs):
    resource = kwargs.get('resource')

    # Connect to Azure Management Service
    set_progress("Connecting To Azure Management Service...")
    azure = AzureARMHandler.objects.first()
    subscription_id = azure.serviceaccount
    credentials = ServicePrincipalCredentials(
        client_id=azure.client_id,
        secret=azure.secret,
        tenant=azure.tenant_id
    )
    web_client = WebSiteManagementClient(credentials, subscription_id)
    set_progress("Successfully Connected To Azure Management Service!")

    # Restart Web App
    web_client.web_apps.restart(resource_group_name=resource.resource_group_name, name=resource.name)