"""
Creates website in Azure.

Service Plan parameter to be dependant(regenerate options) on Resource Group

"""
from common.methods import set_progress
from infrastructure.models import CustomField
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.web import WebSiteManagementClient
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.web.models import AppServicePlan, SkuDescription, Site
from resources.models import ResourceType, Resource

def generate_options_for_location(Server=None, **kwargs):
    location = []
    azure = AzureARMHandler.objects.first()
    for loc in azure.get_all_locations():
        location.append(loc['display_name'])
    return(location)

def generate_options_for_resource_groups(Server=None, **kwargs):
    resource_group = []
    azure = AzureARMHandler.objects.first()
    for rg in azure.armresourcegroup_set.all():
        resource_group.append(rg)
    return(resource_group)

def generate_options_for_service_plans(Server=None, form_prefix=None, form_data=None, **kwargs):
    results = []
    azure = AzureARMHandler.objects.first()
    subscription_id = azure.serviceaccount
    credentials = ServicePrincipalCredentials(
        client_id=azure.client_id,
        secret=azure.secret,
        tenant=azure.tenant_id
    )
    web_client = WebSiteManagementClient(credentials, subscription_id)
    service_plan = CustomField.objects.filter(name__startswith='service_plan').first()
    resource_group = None
    if service_plan:
        control = service_plan.get_control_values_from_form_data(form_prefix, form_data)
        if control:
            keys = control.keys()
            for k in keys:
                if 'resource_group' in k:
                    resource_group = control[k][0]
    if resource_group:
        try:
            for sp in web_client.app_service_plans.list_by_resource_group(resource_group_name=resource_group):
                results.append(sp.name)
        except:
            pass
    return results

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

    # Create Resource Group if Needed
    resource_group = '{{ resource_groups }}'

    # Create App Service Plan if Needed
    service_plan = '{{ service_plans }}'
    service_plan_obj = web_client.app_service_plans.get(resource_group_name=resource_group, name=service_plan)

    # Create Web App
    site_async_operation = web_client.web_apps.create_or_update(
        resource_group,
        resource.name,
        Site(
            location=service_plan_obj.location,
            server_farm_id=service_plan_obj.id
        )
    )
    site = site_async_operation.result()

    # Store Web App metadata on the resource as parameters for teardown
    resource.set_value_for_custom_field(cf_name='web_app_id', value=site.id)
    resource.set_value_for_custom_field(cf_name='resource_group_name', value=resource_group)
    resource.set_value_for_custom_field(cf_name='web_app_location', value=service_plan_obj.location)
    resource.set_value_for_custom_field(cf_name='web_app_default_host_name', value=site.default_host_name)
