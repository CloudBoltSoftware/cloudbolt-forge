"""
A plugin which creates a resource group and applies it to all items within a deployed resource.
Put this plugin as the first build item in a blueprint containing Azure server tiers.
It's important that this plugin is run before provisioning any servers in the build sequence, in order
for those servers to be added to this resource group.

This plugin will create a resource group in Azure, by default naming it after the deployed resource. It will
then add that resource group to the order such that the servers created in the same blueprint order are
created in the new resource group.

Because resource groups are specific to an Azure account and a location, this plugin requires you to select
an environment (from the action input) to create the resource group in a given Azure resource handler
and region. The environment you select when ordering the BP must match the environment for the Azure
VMs being created. Otherwise, any following provision jobs will fail due to the resource group not being
found in the given region that the VM is being created in.
"""
from common.methods import set_progress
from infrastructure.models import CustomField, Environment
from orders.models import BlueprintOrderItem, CustomFieldValue
from resourcehandlers.azure_arm.models import AzureARMHandler, ARMResourceGroup
from servicecatalog.models import ProvisionServerServiceItem
from django.utils.text import slugify


def run(job, *args, **kwargs):
    """
    Creates a resource group, a CFV for this new resource group and
    sets it on the blueprint item arguments so that it later gets set on all servers being created.
    """
    # Name the new resource group after the resource. Here is where you may want to set the resource group name
    # more programmatically using context variables.
    resource = kwargs.get('resource')
    resource_group_name = slugify(resource.name)

    # Get the environment from an action input and then get the resource handler and location from that environment.
    env_id = "{{ azure_environment }}"
    env = Environment.objects.get(id=env_id)
    rh = env.resource_handler.cast()
    location = rh.get_env_location(env)
    
    set_progress(f"Creating new resource group '{resource_group_name}' in region {location}")
    
    # Create the new resource group in Azure and then create a CB ResourceGroup object for it.
    wrapper = rh.get_api_wrapper()
    resource_group_name = wrapper.create_resource_group(resource_group_name, location, add_suffix=True)
    
    try:
        ARMResourceGroup.objects.get_or_create(
            name=resource_group_name,
            handler=rh,
            environment=env)
    except ARMResourceGroup.MultipleObjectsReturned as e:
        # It's possible, but unlikely that we're trying to create a resource group which already exists AND
        # there is a duplicate. In this case, use the first one. It won't matter which one since we
        # only store them by name on the AzureARMServerInfo.
        set_progress(f"More than one Resource group was found with the name: {resource_group_name}. Using "
                     f"the first occurrence. Original exception: {e}")
    
    # Set this resource group on the blueprint item arguments so that it is later
    # used on all servers and Azure resources being created. 
    boi_id = kwargs.get('blueprint_order_item')
    boi = BlueprintOrderItem.objects.get(id=int(boi_id))
    
    cf = CustomField.objects.get(name='resource_group_arm')
    cfv, _ = CustomFieldValue.objects.get_or_create(field=cf, value=resource_group_name)
    cfvs = {cf.name: cfv.value}
    
    # Get each PSSI and update it's BIA with the new Resource group CFV 
    for si in boi.service_items.all():
        si = si.cast()
        if isinstance(si, ProvisionServerServiceItem):
            bia = si.blueprintitemarguments_set.filter(boi=boi).first()
            set_progress(f"Associating the value for the resource group {resource_group_name} with the blueprint item arguments for"
                         f" service item {si} and order item {boi}.")
            si.update_bia_with_param_values(bia, cfvs)

    output = f"Successfully created resource group '{resource_group_name}' and associated it with the order items"
    errors = ""
    return 'SUCCESS', output, errors
    

def generate_options_for_azure_environment(*args, **kwargs):
    """
    Get all Azure environments configured for this blueprint.
    """
    bp = kwargs.get('blueprint')
    envs = set()

    for si in ProvisionServerServiceItem.objects.filter(blueprint_id=bp.id):
        # get enabled envs
        for group in bp.groups.all():
            envs |= si.enabled_envs_for_group(group, only_configured=True)

    options = [(env.id, env.name) for env in envs]

    return options
