"""
Restart Azure Web App
"""
from common.methods import set_progress
from azure.mgmt.web import WebSiteManagementClient
from resourcehandlers.azure_arm.models import AzureARMHandler
from resourcehandlers.azure_arm.azure_wrapper import configure_arm_client


def run(job, **kwargs):
    resource = kwargs.get('resource')

    # Connect to Azure Management Service
    set_progress("Connecting To Azure Management Service...")
    azure = AzureARMHandler.objects.first()
    wrapper = azure.get_api_wrapper()
    web_client = configure_arm_client(wrapper, WebSiteManagementClient)
    set_progress("Successfully Connected To Azure Management Service!")

    # Restart Web App
    web_client.web_apps.restart(resource_group_name=resource.resource_group_name, name=resource.name)