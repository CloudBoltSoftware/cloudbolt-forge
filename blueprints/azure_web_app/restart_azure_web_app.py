"""
Restart Azure Web App
"""
from common.methods import set_progress
from azure.mgmt.web import WebSiteManagementClient
from resourcehandlers.azure_arm.models import AzureARMHandler


def run(job, **kwargs):
    resource = kwargs.get('resource')

    # Connect to Azure Management Service
    set_progress("Connecting To Azure Management Service...")
    azure = AzureARMHandler.objects.first()
    subscription_id = azure.serviceaccount
    credentials = azure.get_api_wrapper().credentials
    web_client = WebSiteManagementClient(credentials, subscription_id)
    set_progress("Successfully Connected To Azure Management Service!")

    # Restart Web App
    web_client.web_apps.restart(resource_group_name=resource.resource_group_name, name=resource.name)