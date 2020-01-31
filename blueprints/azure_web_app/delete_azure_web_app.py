"""
Deletes Web App from Azure
"""
from azure.mgmt.web import WebSiteManagementClient
from common.methods import set_progress
from resourcehandlers.azure_arm.models import AzureARMHandler
from resourcehandlers.azure_arm.azure_wrapper import configure_arm_client


def run(job, **kwargs):
    # Run as Resource teardown management command
    resource = job.resource_set.first()

    # Connect to Azure Management Service
    set_progress("Connecting To Azure Management Service...")
    azure = AzureARMHandler.objects.first()
    wrapper = azure.get_api_wrapper()
    web_client = configure_arm_client(wrapper, WebSiteManagementClient)
    set_progress("Successfully Connected To Azure Management Service!")

    # Use custom field web_app_id to get web app from Azure
    rg = resource.attributes.get(field__name__startswith='resource_group_name')

    # Delete the web app
    web_client.web_apps.delete(resource_group_name=rg.value, name=resource.name)