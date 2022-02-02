"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
import requests
import json
from common.methods import set_progress
from accounts.models import Group
from infrastructure.models import CustomField, Environment
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

def get_or_create_custom_fields():
    """
    Get or create custom fields
    """
    CustomField.objects.get_or_create(
        name="azure_region",
        type="STR",
        defaults={
            'label': "Region",
            'description': 'Location for all resources.',
            'required': True,
            'show_on_servers':True
        }
    )
    
    CustomField.objects.get_or_create(
        name="resource_group",
        type="STR",
        defaults={
            'label': "Resource Group",
            'description': 'Used by the Azure blueprints',
            'required': True,
        }
    )
    
    CustomField.objects.get_or_create(
        name="workspace_name",
        type="STR",
        defaults={
            'label': "Workspace Name",
            'description': 'The name of the Azure Databricks workspace to create.',
            'required': True,
        }
    )

    CustomField.objects.get_or_create(
        name="pricing_tier",
        type="STR",
        defaults={
            'label': "Pricing Tier",
            'description': 'The pricing tier of workspace.',
            'required': True,
        }
    )
    
    CustomField.objects.get_or_create(
        name="disable_public_ip",
        type="BOOL",
        defaults={
            'label': "Disable Public IP",
            'description': 'Specifies whether to deploy Azure Databricks workspace with Secure Cluster Connectivity (No Public IP) enabled or not',
            'required': True,
        }
    )
    
    CustomField.objects.get_or_create(
        name="azure_resource_id",
        type="STR",
        defaults={
            'label': "Azure resoruce id",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
             'show_on_servers':True
        }
    )
    
    CustomField.objects.get_or_create(
        name="azure_deployment_id",
        type="STR",
        defaults={
            'label': "Azure deployment id",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
        }
    )
    
    CustomField.objects.get_or_create(
        name="azure_correlation_id",
        type="STR",
        defaults={
            'label': "Azure Databricks Correlation Id",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
        }
    )
    
    CustomField.objects.get_or_create(
        name="azure_rh_id",
        type="STR",
        defaults={
            'label': "Azure Resource Id",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
        }
    )
    
    CustomField.objects.get_or_create(
        name="azure_dbs_workspace_url",
        type="STR",
        defaults={
            'label': "Azure api version",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
        }
    )
    
    CustomField.objects.get_or_create(
        name="azure_api_version",
        type="STR",
        defaults={
            'label': "Azure Databricks Workspace URL",
            'description': 'Used by the ARM Template blueprint.',
            'required': False,
        }
    )


def get_arm_template():
    arm_temp = """{
      "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
      "contentVersion": "1.0.0.0",
      "parameters": {
        "disablePublicIp": {
          "type": "bool",
          "defaultValue": false,
          "metadata": {
            "description": "Specifies whether to deploy Azure Databricks workspace with Secure Cluster Connectivity (No Public IP) enabled or not"
          }
        },
        "workspaceName": {
          "type": "string",
          "metadata": {
            "description": "The name of the Azure Databricks workspace to create."
          }
        },
        "pricingTier": {
          "type": "string",
          "defaultValue": "premium",
          "allowedValues": [
            "standard",
            "premium"
          ],
          "metadata": {
            "description": "The pricing tier of workspace."
          }
        },
        "vnetAddressPrefix": {
          "type": "string",
          "defaultValue": "10.139",
          "metadata": {
            "description": "The first 2 octets of the virtual network /16 address range (e.g., '10.139' for the address range 10.139.0.0/16)."
          }
        },
        "location": {
          "type": "string",
          "defaultValue": "[resourceGroup().location]",
          "metadata": {
            "description": "Location for all resources."
          }
        }
      },
      "variables": {
        "managedResourceGroupName": "[concat('databricks-rg-', parameters('workspaceName'), '-', uniqueString(parameters('workspaceName'), resourceGroup().id))]"
      },
      "resources": [
        {
          "type": "Microsoft.Databricks/workspaces",
          "name": "[parameters('workspaceName')]",
          "location": "[parameters('location')]",
          "apiVersion": "2018-04-01",
          "sku": {
            "name": "[parameters('pricingTier')]"
          },
          "properties": {
            "ManagedResourceGroupId": "[subscriptionResourceId('Microsoft.Resources/resourceGroups', variables('managedResourceGroupName'))]",
            "parameters": {
              "vnetAddressPrefix": {
                "value": "[parameters('vnetAddressPrefix')]"
              },
              "enableNoPublicIp": {
                "value": "[parameters('disablePublicIp')]"
              }
            }
          }
        }
      ],
      "outputs": {
        "workspace": {
          "type": "object",
          "value": "[reference(resourceId('Microsoft.Databricks/workspaces', parameters('workspaceName')))]"
        }
      }
    }"""
    
    return arm_temp
    
    
def generate_options_for_azure_region(**kwargs):
    group_name = kwargs["group"]

    try:
        group = Group.objects.get(name=group_name)
    except Exception as err:
        return None
    
    # fetch all group environment
    envs = group.get_available_environments()
    options=[]

    for env in envs:
        if env.resource_handler:
            if env.resource_handler.resource_technology:
                if env.resource_handler.resource_technology.name == "Azure":
                    options.append((env.id, env.name))
                    
    if not options:
        raise RuntimeError(
            "No valid Environments on Azure resource handlers in CloudBolt"
        )
        
    return options


def generate_options_for_resource_group(field, control_value=None, **kwargs):
    options = []
    
    if not control_value:
        options.insert(0, ('', '--- First, Select an Environment ---'))
        return options

    # get env object by id
    env = Environment.objects.get(id=control_value)
    
    wrapper = env.resource_handler.cast().get_api_wrapper()
    
    # fetch all resource groups
    resource_groups = wrapper.resource_client.client.resource_groups.list(location=env.node_location)

    for rgs in resource_groups:
        if env.node_location == rgs.location and rgs.managed_by is None:
            options.append((rgs.name, rgs.name))
    
    if options:
        options.insert(0, ('', '--- Select a Resource Group ---'))
    else:
        options.insert(0, ('', '--- No Resource Groups found in this Environment ---'))
    
    return options
    

def generate_options_for_pricing_tier(field, **kwargs):
    # ("trial", "Trial (Premium - 14 Days Free DBUs)")
    
    return [("standard", "Standard (Apache Spark, Secure with Azure AD)"), 
                ("premium", "Premium (+ Role base access controls)")]


def run(job, *args, **kwargs):
    set_progress("Starting Provision of the databricks template...")
    
    resource = kwargs.get('resource')
    
    region = "{{azure_region}}"
    resource_group = "{{resource_group}}"
    workspace_name = "{{workspace_name}}"
    pricing_tier = "{{pricing_tier}}"
    disable_public_ip = "{{ disable_public_ip }}"
    
    # get or create custom fields
    get_or_create_custom_fields()
    
    # Get environment object
    env = Environment.objects.get(id=region)
    
    # Get resource handler object
    rh = env.resource_handler.cast()
    
    deployment_name = f'{workspace_name}-{job.id}'
    disable_public_ip = False if disable_public_ip == "False" else True
    
    resource.name = deployment_name
    
    # Create Parameter inputs dict
    params_dict = {
        "disablePublicIp": disable_public_ip ,
        "workspaceName": deployment_name,
        "pricingTier": pricing_tier,
        "vnetAddressPrefix": "10.139",
        "location": env.node_location
    }
    
    # Generic ARM Params
    timeout = 900
    
    # Get the ARM template json
    template = json.loads(get_arm_template())
    
    logger.debug(f'Submitting request for Databricks template. deployment_name: '
                 f'{deployment_name}, resource_group: {resource_group}, '
                 f'template: {template}')
    set_progress(f'Submitting Databricks request to Azure. This can take a while.'
                 f' Timeout is set to: {timeout}')
    
    wrapper = rh.get_api_wrapper()
    
    # deploy databricks workspace
    deployment = wrapper.deploy_template(deployment_name, resource_group,
                                         template, params_dict,
                                         timeout=timeout)

    set_progress(f'Databricks created successfully')
    logger.debug(f'deployment info: {deployment}')
    
    deploy_props = deployment.properties
    
    resource.azure_rh_id = rh.id
    resource.workspace_name = deployment_name
    resource.pricing_tier = pricing_tier
    resource.disable_public_ip = disable_public_ip
    resource.azure_dbs_workspace_url = deploy_props.outputs['workspace']['value']['workspaceUrl']
    resource.azure_region = env.node_location
    resource.azure_deployment_id = deployment.id
    resource.azure_resource_id = deploy_props.additional_properties['outputResources'][0]['id']
    resource.azure_correlation_id = deploy_props.correlation_id
    resource.resource_group = resource_group
    resource.save()
    

    return "SUCCESS", "Databricks deployed successfully", ""