"""
Deletes Web App from Azure
"""
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.web import WebSiteManagementClient
from common.methods import set_progress
from infrastructure.models import CustomField
from jobs.models import Job
from resourcehandlers.azure_arm.models import AzureARMHandler
from resources.models import ResourceType, Resource

def run(job, **kwargs):
    # Run as Resource teardown management command
    resource = job.resource_set.first()

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

    # Use custom field web_app_id to get web app from Azure
    rg = resource.attributes.get(field__name__startswith='resource_group_name')

    # Delete the web app
    web_client.web_apps.delete(resource_group_name=rg.value, name=resource.name)