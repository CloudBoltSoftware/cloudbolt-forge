"""
Creates web-app in Azure.
"""
import random

from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from resourcehandlers.azure_arm.models import ARMResourceGroup

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.web.models import AppServicePlan, SkuDescription, Site


def generate_options_for_azure_env(**kwargs):
    options = []

    for env in Environment.objects.filter(
        resource_handler__resource_technology__name="Azure"
    ):
        options.append((env.id, env.name))
    return sorted(options, key=lambda tup: tup[1].lower())


def generate_options_for_resource_groups(control_value=None, **kwargs):
    if control_value is None:
        return []
    env = Environment.objects.get(id=control_value)
    groups = env.armresourcegroup_set.all()

    return [(g.id, g.name) for g in groups]


def generate_options_for_service_plan_name(control_value=None, **kwargs):
    # Provide an empty option to auto-create a new service plan.
    options = [('', 'Auto-create new Service Plan')]

    if control_value is None or control_value is "":
        return options

    rg = ARMResourceGroup.objects.get(id=control_value)
    web_client = _get_client(rg.handler)

    for service_plan in web_client.app_service_plans.list_by_resource_group(
        resource_group_name=rg.name
    ):
        options.append((service_plan.name, service_plan.name))

    return options


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

    set_progress("Connecting To Azure Management Service...")

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


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name="azure_web_app_name",
        type="STR",
        defaults={
            "label": "Azure Web App Name",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="azure_web_app_default_host_name",
        type="STR",
        defaults={
            "label": "Azure Server Name",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="azure_location",
        type="STR",
        defaults={
            "label": "Azure Location",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="azure_resource_group_name",
        type="STR",
        defaults={
            "label": "Azure Resource Group",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="azure_web_app_id",
        type="STR",
        defaults={
            "label": "Azure Web App Id",
            "description": "Application ID in Azure",
            "show_as_attribute": True,
        },
    )


def run(job, **kwargs):
    resource = kwargs.get("resource")
    create_custom_fields_as_needed()

    env_id = "{{ azure_env }}"
    resource_group_id = "{{ resource_groups }}"
    web_app_name = "{{ web_app_name }}"
    service_plan_name = "{{ service_plan_name }}"

    set_progress(
        f"Environment {env_id} ResourceId {resource_group_id} And KWARGS {kwargs}"
    )

    # Clean Resource name to Azure acceptable web-app name
    web_app_name = web_app_name.replace(" ", "-")
    web_app_name = web_app_name.replace("(", "-")
    web_app_name = web_app_name.replace(")", "")

    resource_group = ARMResourceGroup.objects.get(id=resource_group_id)

    # Connect to Azure Management Service
    web_client = _get_client(resource_group.handler)

    if service_plan_name:
        # User selected a pre-existing service plan, so just get it.
        service_plan_obj = web_client.app_service_plans.get(
            resource_group_name=resource_group.name, name=service_plan_name
        )
    else:
        # Auto-create a new service plan.
        # Use the web_app_name and append 5 random digits to have a decent probability of uniqueness.
        service_plan_name = web_app_name + '-' + str(random.randint(10000, 99999))

        set_progress(f"Environment {env_id}")
        env = Environment.objects.get(id=env_id)
        service_plan_async_operation = web_client.app_service_plans.create_or_update(
            resource_group.name,
            service_plan_name,
            AppServicePlan(
                app_service_plan_name=service_plan_name,
                location=env.node_location,
                sku=SkuDescription(name="S1", capacity=1, tier="Standard"),
            ),
        )
        service_plan_async_operation.result()

        service_plan_obj = web_client.app_service_plans.get(
            resource_group_name=resource_group.name, name=service_plan_name
        )

    # Create Web App
    site_async_operation = web_client.web_apps.create_or_update(
        resource_group.name,
        web_app_name,
        Site(location=service_plan_obj.location, server_farm_id=service_plan_obj.id),
    )
    site = site_async_operation.result()

    # Store Web App metadata on the resource as parameters for teardown
    resource.azure_web_app_name = web_app_name
    resource.name = web_app_name
    resource.azure_web_app_id = site.id
    resource.azure_web_app_default_host_name = site.default_host_name
    resource.resource_group_name = resource_group
    resource.azure_location = site.location
    resource.save()

    return "SUCCESS", "", ""
