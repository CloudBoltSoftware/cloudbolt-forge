"""
Creates an Azure virtual network.
"""
from common.methods import set_progress
from infrastructure.models import CustomField
from infrastructure.models import Environment
from azure.common.credentials import ServicePrincipalCredentials
from msrestazure.azure_exceptions import CloudError
from azure.mgmt.network import NetworkManagementClient


def generate_options_for_env_id(server=None, **kwargs):
    envs = Environment.objects.filter(
        resource_handler__resource_technology__name="Azure")
    options = [(env.id, env.name) for env in envs]
    return options

def generate_options_for_resource_group(control_value=None, **kwargs):
    if control_value is None:
        return []
    env = Environment.objects.get(id=control_value)
    rh = env.resource_handler.cast()
    return list(rh.armresourcegroup_set.values_list('name',flat=True))

def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='azure_rh_id', type='STR',
        defaults={'label':'Azure RH ID', 'description':'Used by the Azure blueprints', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='azure_virtual_net_name', type='STR',
        defaults={'label':'Azure Virtual network Name', 'description':'Used by the Azure VPN blueprint', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='azure_virtual_net_id', type='STR',
        defaults={'label':'Azure Virtual network ID', 'description':'Used by the Azure VPN blueprint', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='azure_subnet_names', type='STR',
        defaults={'label':'Azure Subnet Name', 'description':'Used by the Azure VPN blueprint', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='azure_location', type='STR',
        defaults={'label':'Azure Location', 'description':'Used by the Azure blueprints', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='resource_group_name', type='STR',
        defaults={'label':'Azure Resource Group', 'description':'Used by the Azure blueprints', 'show_as_attribute':True}
    )

    CustomField.objects.get_or_create(
        name='vpn_adress_prefixes', type='STR',
        defaults={'label':'Azure vpn adress space', 'description':'Used by the Azure vpn blueprint', 'show_as_attribute':True}
    )

def run(job, **kwargs):
    resource = kwargs.get('resource')
    create_custom_fields_as_needed()
    env_id = '{{ env_id }}'
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    location = env.node_location

    resource_group = '{{ resource_group }}'
    virtual_net_name = '{{ virtual_net_name }}'
    vpn_adress_prefix = '{{ vpn_adress_prefix }}'
    subnet_adress_prefix = '{{ subnet_adress_prefix }}'
    subnet_name = virtual_net_name + '_subnet'

    set_progress("Connecting To Azure...")
    credentials = ServicePrincipalCredentials(
        client_id=rh.client_id,
        secret=rh.secret,
        tenant=rh.tenant_id,
    )
    network_client = NetworkManagementClient(credentials, rh.serviceaccount)
    set_progress("Connection to Azure established")

    #create the vpn
    set_progress('Creating virtual network "%s"...' % virtual_net_name)
    try:
        async_vnet_creation = network_client.virtual_networks.create_or_update(
            resource_group,
            virtual_net_name,
            {
                'location': location,
                'address_space': {
                    'address_prefixes': [vpn_adress_prefix]
                }
            }
        )
        async_vnet_creation.wait()
    except CloudError as e:
        set_progress('Azure Clouderror: {}'.format(e))

    #create the subnet
    set_progress('Creating subnet "%s"...' % subnet_name)
    try:
        async_subnet_creation = network_client.subnets.create_or_update(
            resource_group,
            virtual_net_name,
            subnet_name,
            {'address_prefix': subnet_adress_prefix}
        )
        subnet_info = async_subnet_creation.result()
    except CloudError as e:
        set_progress("Azure Clouderror: {}".format(e))
        return "FAILURE", "Virtual network could not be created", e
    
    assert subnet_info.name == subnet_name
    set_progress('Subnet "%s" has been created.' % subnet_name)

    resource.name = virtual_net_name + " - " + resource_group
    resource.azure_virtual_net_name = virtual_net_name
    resource.vpn_adress_prefix = vpn_adress_prefix
    resource.resource_group_name = resource_group
    resource.azure_location = location
    resource.azure_rh_id = rh.id
    resource.azure_subnet_name = subnet_name
    resource.save()

    return "SUCCESS", "The vpn and subnet have been successfully created", ""