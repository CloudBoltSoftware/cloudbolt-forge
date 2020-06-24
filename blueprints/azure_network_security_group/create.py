"""
Creates an Azure network security group
"""
import settings

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.network import NetworkManagementClient
from msrestazure.azure_exceptions import CloudError

from common.methods import is_version_newer, set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment


cb_version = settings.VERSION_INFO["VERSION"]
CB_VERSION_93_PLUS = is_version_newer(cb_version, "9.2.2")


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Azure"
    )
    options = [(env.id, env.name) for env in envs]
    return options


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


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name="azure_rh_id",
        type="STR",
        defaults={
            "label": "Azure RH ID",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )

    CustomField.objects.get_or_create(
        name="azure_network_security_group",
        type="STR",
        defaults={
            "label": "Azure Network Security group name",
            "description": "Used by the Azure NSG",
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
        name="resource_group_name",
        type="STR",
        defaults={
            "label": "Azure Resource Group",
            "description": "Used by the Azure blueprints",
            "show_as_attribute": True,
        },
    )


def run(job, **kwargs):
    resource = kwargs.get("resource")

    env_id = "{{ env_id }}"
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    location = env.node_location
    set_progress("Location: %s" % location)

    resource_group = "{{ resource_group }}"
    network_security_group_name = "{{ network_security_group_name }}"

    create_custom_fields_as_needed()

    set_progress("Connecting To Azure Network Service...")

    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id, secret=rh.secret, tenant=rh.tenant_id,
    )
    network_client = NetworkManagementClient(credentials, rh.serviceaccount)
    set_progress("Connection to Azure networks established")

    set_progress("Creating the network security group...")
    security_rule_parameters = {
        "location": location,
    }
    try:
        async_vnet_creation = network_client.network_security_groups.create_or_update(
            resource_group, network_security_group_name, security_rule_parameters
        )
        nsg_info = async_vnet_creation.result()
    except CloudError as e:
        set_progress("Azure Clouderror: {}".format(e))

    assert nsg_info.name == network_security_group_name

    resource.name = "Azure NSG - " + network_security_group_name
    resource.azure_network_security_group = network_security_group_name
    resource.resource_group_name = resource_group
    resource.azure_location = location
    resource.azure_rh_id = rh.id
    resource.save()

    return (
        "SUCCESS",
        "Network security group {} has been created in Location {}.".format(
            network_security_group_name, location
        ),
        "",
    )
