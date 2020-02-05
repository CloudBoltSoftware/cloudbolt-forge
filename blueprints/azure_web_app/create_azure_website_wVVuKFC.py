"""
Creates website in Azure.

Service Plan parameter to be dependant(regenerate options) on Resource Group

"""
from common.methods import set_progress
from infrastructure.models import CustomField
from azure.mgmt.web import WebSiteManagementClient
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.web.models import AppServicePlan, SkuDescription, Site
from azure.common.credentials import ServicePrincipalCredentials


def _get_client(handler):
    """
    Get the clients using newer methods from the CloudBolt main repo if this CB is running
    a version greater than 9.2. These internal methods implicitly take care of much of the other
    features in CloudBolt such as proxy and ssl verification.
    Otherwise, manually instantiate clients without support for those other CloudBolt settings.
    :param handler:
    :return:
    """
    import settings
    from common.methods import is_version_newer

    set_progress("Connecting To Azure...")

    cb_version = settings.VERSION_INFO["VERSION"]
    if is_version_newer(cb_version, "9.2"):
        from resourcehandlers.azure_arm.azure_wrapper import configure_arm_client

        wrapper = handler.get_api_wrapper()
        web_client = configure_arm_client(wrapper, WebSiteManagementClient)
    else:
        # TODO: Remove once versions <= 9.2 are no longer supported.
        credentials = ServicePrincipalCredentials(
            client_id=handler.client_id,
            secret=handler.secret,
            tenant=handler.tenant_id,
        )
        web_client = WebSiteManagementClient(credentials, handler.serviceaccount)

    set_progress("Connection to Azure established")

    return web_client


def generate_options_for_resource_groups(server=None, **kwargs):

    resource_group = []
    azure = AzureARMHandler.objects.first()
    for rg in azure.armresourcegroup_set.all():
        resource_group.append(rg)

    return resource_group


def generate_options_for_service_plans(
    server=None, form_prefix=None, form_data=None, **kwargs
):
    results = []

    azure = AzureARMHandler.objects.first()
    web_client = _get_client(azure)

    service_plan = CustomField.objects.filter(name__contains="service_plan").first()
    resource_group = None

    if service_plan:
        control = service_plan.get_control_values_from_form_data(form_prefix, form_data)

        if control:
            keys = control.keys()
            for k in keys:
                if "resource_group" in k:
                    # Extract from the control data structure, ex: {'resource_group_a123': ['rgName']}
                    resource_group = control[k][0]

    if resource_group:
        try:
            for sp in web_client.app_service_plans.list_by_resource_group(
                resource_group_name=resource_group
            ):
                results.append(sp.name)
        except:
            pass
    return results


def run(job, **kwargs):
    resource = kwargs.get("resource")

    # Connect to Azure Management Service
    azure = AzureARMHandler.objects.first()
    web_client = _get_client(azure)

    # Create Resource Group if Needed
    resource_group = "{{ resource_groups }}"

    # Create App Service Plan if Needed
    service_plan = "{{ service_plans }}"
    service_plan_obj = web_client.app_service_plans.get(
        resource_group_name=resource_group, name=service_plan
    )

    # Create Web App
    site_async_operation = web_client.web_apps.create_or_update(
        resource_group,
        resource.name,
        Site(location=service_plan_obj.location, server_farm_id=service_plan_obj.id),
    )
    site = site_async_operation.result()

    # Store Web App metadata on the resource as parameters for teardown
    resource.set_value_for_custom_field(cf_name="web_app_id", value=site.id)
    resource.set_value_for_custom_field(
        cf_name="resource_group_name", value=resource_group
    )
    resource.set_value_for_custom_field(
        cf_name="web_app_location", value=service_plan_obj.location
    )
    resource.set_value_for_custom_field(
        cf_name="web_app_default_host_name", value=site.default_host_name
    )
