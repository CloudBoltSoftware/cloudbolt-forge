"""
Creates web-app in Azure.
"""
import random
import settings

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.web.models import AppServicePlan, SkuDescription, Site

from common.methods import is_version_newer, set_progress
from infrastructure.models import CustomField, Environment
from resourcehandlers.azure_arm.models import AzureARMHandler


cb_version = settings.VERSION_INFO["VERSION"]
CB_VERSION_93_PLUS = is_version_newer(cb_version, "9.2.1")


def generate_options_for_azure_env(**kwargs):
    options = []

    for env in Environment.objects.filter(
        resource_handler__resource_technology__name="Azure"
    ):
        options.append((env.id, env.name))
    return sorted(options, key=lambda tup: tup[1].lower())


def generate_options_for_resource_group(control_value=None, **kwargs):
    """Dynamically generate options for resource group form field based on the user's selection for Environment.
    
    This method requires the user to set the resource_group parameter as dependent on environment.
    """
    if control_value is None:
        return []

    env = Environment.objects.get(id=control_value)

    if CB_VERSION_93_PLUS:
        # Get the Resource Groups as defined on the Environment. The Resource Group is a
        # CustomField that is only updated on the Env when the user syncs this field on the
        # Environment specific parameters.
        resource_groups = env.custom_field_options.filter(
            field__name="resource_group_arm"
        )
        return [rg.str_value for rg in resource_groups]
    else:
        rh = env.resource_handler.cast()
        groups = rh.armresourcegroup_set.all()
        return [g.name for g in groups]


def generate_options_for_service_plan_name(control_value=None, **kwargs):
    # Provide an empty option to auto-create a new service plan.
    options = [("", "Auto-create new Service Plan")]

    if control_value is None or control_value == "":
        return options

    if CB_VERSION_93_PLUS:
        # Get the Resource Group. There may be multiple Azure RHs and Environments that
        # have Resource Group CustomField.

        arm_resource_handlers = AzureARMHandler.objects.all()
        for rh in arm_resource_handlers:

            try:
                web_client = _get_client(rh)
                for service_plan in web_client.app_service_plans.list_by_resource_group(
                    resource_group_name=control_value
                ):
                    options.append((service_plan.name, service_plan.name))

            # The exceptions cannot be seen as this method generates return values for
            # a web form dropdown. The return is either a list that contains a value,
            # or an empty list.
            except Exception:
                pass

        return options

    else:
        from resourcehandlers.azure_arm.models import ARMResourceGroup

        rg = ARMResourceGroup.objects.get(name=control_value)
        web_client = _get_client(rg.handler)

        try:
            for service_plan in web_client.app_service_plans.list_by_resource_group(
                resource_group_name=rg.name
            ):
                options.append((service_plan.name, service_plan.name))

        # The exceptions cannot be seen as this method generates return values for
        # a web form dropdown. The return is either a list that contains a value,
        # or an empty list.
        except Exception:
            pass

        return options


def _get_client(handler):
    """
    Get the clients using newer methods from the CloudBolt main repo if this CB is running
    a version greater than 9.2.1. These internal methods implicitly take care of much of the other
    features in CloudBolt such as proxy and ssl verification.
    Otherwise, manually instantiate clients without support for those other CloudBolt settings.
    :param handler:
    :return:
    """

    set_progress("Connecting To Azure...")

    if CB_VERSION_93_PLUS:
        from resourcehandlers.azure_arm.azure_wrapper import configure_arm_client

        wrapper = handler.get_api_wrapper()
        web_client = configure_arm_client(wrapper, WebSiteManagementClient)
        set_progress("Connection to Azure established")
        return web_client
    else:
        # TODO: Remove once versions <= 9.2.1 are no longer supported.
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
    resource_group = "{{ resource_group }}"
    web_app_name = "{{ web_app_name }}"
    service_plan_name = "{{ service_plan_name }}"

    set_progress(
        f"Environment {env_id} ResourceId {resource_group} And KWARGS {kwargs}"
    )

    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()

    # Clean Resource name to Azure acceptable web-app name
    web_app_name = web_app_name.replace(" ", "-")
    web_app_name = web_app_name.replace("(", "-")
    web_app_name = web_app_name.replace(")", "")

    # Connect to Azure Management Service
    set_progress("Connecting To Azure Management Service...")
    web_client = _get_client(rh)
    set_progress("Successfully Connected To Azure Management Service!")

    if service_plan_name:
        # User selected a pre-existing service plan, so just get it.
        service_plan_obj = web_client.app_service_plans.get(
            resource_group_name=resource_group, name=service_plan_name
        )
    else:
        # Auto-create a new service plan.
        # Use the web_app_name and append 5 random digits to have a decent probability of uniqueness.

        service_plan_name = web_app_name + "-{}".format(random.randint(10000, 99999))

        set_progress(f"Environment {env_id}")
        env = Environment.objects.get(id=env_id)
        service_plan_async_operation = web_client.app_service_plans.create_or_update(
            resource_group_name=resource_group,
            name=service_plan_name,
            app_service_plan=AppServicePlan(
                location=env.node_location,
                app_service_plan_name=service_plan_name,
                sku=SkuDescription(name="S1", capacity=1, tier="Standard"),
            ),
        )
        service_plan_async_operation.result()

        service_plan_obj = web_client.app_service_plans.get(
            resource_group_name=resource_group, name=service_plan_name
        )

    # Create Web App
    site_async_operation = web_client.web_apps.create_or_update(
        resource_group,
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
