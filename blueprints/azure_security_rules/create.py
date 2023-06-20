"""
Creates an Azure security rule
"""
import settings
from common.methods import set_progress, is_version_newer
from infrastructure.models import CustomField
from infrastructure.models import Environment
from azure.common.credentials import ServicePrincipalCredentials
from resourcehandlers.azure_arm.models import AzureARMHandler
from azure.mgmt.network import NetworkManagementClient
from msrestazure.azure_exceptions import CloudError

cb_version = settings.VERSION_INFO["VERSION"]
CB_VERSION_93_PLUS = is_version_newer(cb_version, "9.2.2")

def get_tenant_id_for_azure(handler):
    '''
        Handling Azure RH table changes for older and newer versions (> 9.4.5)
    '''
    if hasattr(handler,"azure_tenant_id"):
        return handler.azure_tenant_id
    return handler.tenant_id

def generate_options_for_env_id(server=None, **kwargs):
    options = list(Environment.objects.filter(
        resource_handler__resource_technology__name="Azure").values_list('id','name'))
    return options

def generate_options_for_resource_group(control_value=None, **kwargs):
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
    rh = env.resource_handler.cast()
    return list(rh.armresourcegroup_set.values_list('name',flat=True))

def generate_options_for_protocol(server=None, **kwargs):
    return ['Tcp', 'Udp']

def generate_options_for_access(server=None, **kwargs):
    return ['Allow', 'Deny']

def generate_options_for_direction(server=None, **kwargs):
    return ['Inbound', 'Outbound']

def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='azure_rh_id', type='STR',
        defaults={'label': 'Azure RH ID', 'description': 'Used by the Azure blueprints', 'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='azure_location', type='STR',
        defaults={'label': 'Azure Location', 'description': 'Used by the Azure blueprints', 'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='resource_group_name', type='STR',
        defaults={'label': 'Azure Resource Group', 'description': 'Used by the Azure blueprints',
                  'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='azure_network_security_group_name', type='STR',
        defaults={'label': 'Azure Network Security group name', 'description': 'Azure Network Security group name',
                  'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='azure_security_rule_protocol', type='STR',
        defaults={'label': 'Azure Network Security rule protocol', 'description': 'Azure Network Security rule protocol',
                  'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='azure_security_rule_access', type='STR',
        defaults={'label': 'Azure Network Security rule access value', 'description': 'Azure Network Security rule access value',
                  'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='azure_security_rule_direction', type='STR',
        defaults={'label': 'Azure Network Security rule protocol', 'description': 'Azure Network Security rule direction',
                  'show_as_attribute': True}
    )

    CustomField.objects.get_or_create(
        name='azure_security_rule_name', type='STR',
        defaults={'label': 'Azure Network Security rule name', 'description': 'Azure Network Security rule name',
                  'show_as_attribute': True}
    )


def run(job, **kwargs):
    resource = kwargs.get('resource')

    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    location = env.node_location

    resource_group = '{{ resource_group }}'
    azure_network_security_group_name = '{{ azure_network_security_group_name }}'

    protocol = "{{ protocol }}"
    access = "{{ access }}"
    direction = "{{ direction }}"
    source_port_range = "{{ source_port_range }}"
    destination_port_range = "{{ destination_port_range }}"
    source_address_prefix = "{{ source_address_prefix }}"
    priority = "{{ priority }}"
    destination_address_prefix = "{{ destination_address_prefix }}"
    security_rule_name = azure_network_security_group_name + " " + direction

    create_custom_fields_as_needed()

    set_progress("Connecting To Azure Network Service...")

    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id,
        secret=rh.secret,
        tenant=get_tenant_id_for_azure(rh)
    )
    network_client = NetworkManagementClient(credentials, rh.serviceaccount)
    set_progress("Connection to Azure networks established")

    set_progress("Creating the network security group...")
    security_rule_parameters = {
        "location": location,
    }
    try:
        async_vnet_creation = network_client.network_security_groups.create_or_update(
            resource_group,
            azure_network_security_group_name,
            security_rule_parameters
        )
        nsg_info = async_vnet_creation.result()
    except CloudError as e:
        return "FAILURE", "Could not create network security group", e

    assert nsg_info.name == azure_network_security_group_name

    set_progress("creating security rule...")
    security_rule_parameters = {
        "protocol": protocol,
        "access": access,
        "direction": direction,
        "source_port_range": source_port_range,
        "destination_port_range": destination_port_range,
        "source_address_prefix": source_address_prefix,
        "priority": priority,
        "destination_address_prefix": destination_address_prefix
    }

    try:
        async_security_rule_creation = network_client.security_rules.create_or_update(
            resource_group_name = resource_group,
            network_security_group_name = azure_network_security_group_name,
            security_rule_name = security_rule_name,
            security_rule_parameters = security_rule_parameters
        )
        security_rule_info = async_security_rule_creation.result()
    except CloudError as e:
        return "FAILURE", "could not create security rule", e

    assert security_rule_info.name == security_rule_name


    resource.name = 'Azure Security rule - ' + security_rule_name
    resource.resource_group_name = resource_group
    resource.azure_location = location
    resource.azure_rh_id = rh.id
    resource.azure_network_security_group_name = azure_network_security_group_name
    resource.azure_security_rule_protocol = protocol
    resource.azure_security_rule_access = access
    resource.azure_security_rule_direction = direction
    resource.azure_security_rule_name = security_rule_name
    resource.save()
    
    return ("SUCCESS", "Security rule {} has been created in {} network security group.".format(security_rule_name, azure_network_security_group_name), "")