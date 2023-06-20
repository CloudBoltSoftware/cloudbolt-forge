"""
Build service item action for AKS Cluster Deployment

This action uses an ARM Template to create an AKS Cluster
"""
from jobs.models import Job
from utilities.events import add_server_event

if __name__ == "__main__":
    import os
    import sys
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    sys.path.append("/opt/cloudbolt")
    sys.path.append("/var/opt/cloudbolt/proserv")
    django.setup()

from common.methods import set_progress
from infrastructure.models import CustomField, Server
from infrastructure.models import Environment
import json
from utilities.logger import ThreadLogger
from accounts.models import Group

logger = ThreadLogger(__name__)


# TODO: Add in day two with ARM Templates?
# TODO: Should we create RGs every time?

def generate_options_for_env_id(**kwargs):
    group_name = kwargs["group"]
    try:
        group = Group.objects.get(name=group_name)
    except:
        return None
    envs = group.get_available_environments()
    set_progress(f'Available Envs: {envs}')
    options = [('', '--- Select an Environment ---')]
    for env in envs:
        if env.resource_handler:
            if env.resource_handler.resource_technology:
                if env.resource_handler.resource_technology.name == "Azure":
                    options.append((env.id, env.name))
    return options


def generate_options_for_resource_group(field, control_value=None, **kwargs):
    if not control_value:
        options = [('', '--- First, Select an Environment ---')]
        return options

    options = [('', '--- Select a Resource Group ---')]
    env = Environment.objects.get(id=control_value)

    groups = env.custom_field_options.filter(
        field__name='resource_group_arm')
    if groups:
        for g in groups:
            options.append((g.str_value, g.str_value))
        return options
    return [('', 'No Resource Groups found in this Environment')]


def generate_options_for_node_size(field, control_value=None, **kwargs):
    if not control_value:
        options = [('', '--- First, Select an Environment ---')]
        return options

    env = Environment.objects.get(id=control_value)
    cfvs = env.get_cfvs_for_custom_field('node_size')
    options = [(opt.value, opt.value) for opt in cfvs]
    if ('Standard_B4ms', 'Standard_B4ms') in options:
        return {'options': options, 'initial_value': ('Standard_B4ms',
                                                      'Standard_B4ms')}
    if len(options) > 0:
        return options
    return [('', '--- No Node Sizes found in this Environment ---')]


def generate_options_for_kubernetes_version(**kwargs):
    # These options can safely be modified to show the Kubernetes Versions
    # relevant to your environment
    options = [('1.21.2', '1.21.2'), ('1.21.1', '1.21.1'),
               ('1.20.7', '1.20.7'), ('1.20.5', '1.20.5'),
               ('1.19.11', '1.19.11'), ('1.19.9', '1.19.9')]
    return {'options': options, 'initial_value': ('1.20.7', '1.20.7')}


def create_cf(cf_name, cf_label, description, cf_type="STR", required=False,
              **kwargs):
    defaults = {
        'label': cf_label,
        'description': description,
        'required': required,
    }
    for key, value in kwargs.items():
        defaults[key] = value

    cf = CustomField.objects.get_or_create(
        name=cf_name,
        type=cf_type,
        defaults=defaults
    )


def get_or_create_cfs():
    create_cf('azure_rh_id', 'Azure RH ID', 'Used by the Azure blueprints')
    create_cf('azure_region', 'Azure Region', 'Used by the Azure blueprints',
              show_on_servers=True)
    create_cf('azure_deployment_id', 'ARM Deployment ID',
              'Used by the ARM Template blueprint', show_on_servers=True)
    create_cf('azure_correlation_id', 'ARM Correlation ID',
              'Used by the ARM Template blueprint')


def get_provider_type_from_id(resource_id):
    return resource_id.split('/')[6]


def get_resource_type_from_id(resource_id):
    return resource_id.split('/')[7]


def get_api_version_key_from_id(id_value):
    provider_type = get_provider_type_from_id(id_value)
    resource_type = get_resource_type_from_id(id_value)
    ms_type = f'{provider_type}/{resource_type}'
    id_split = id_value.split('/')
    if len(id_split) == 11:
        ms_type = f'{ms_type}/{id_split[9]}'
    ms_type_us = ms_type.replace('.', '').replace('/', '_').lower()
    api_version_key = f'{ms_type_us}_api_version'
    return api_version_key


def get_azure_server_name(id_value):
    return id_value.split('/')[8]


def create_field_set_value(field_name_id, id_value, i, resource):
    create_cf(field_name_id, f'ARM Created Resource {i} ID',
              'Used by the ARM Template blueprint',
              show_on_servers=True)
    resource.set_value_for_custom_field(field_name_id, id_value)
    return resource


def get_arm_template():
    return """
{
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
        "resourceName": {
            "type": "string",
            "metadata": {
                "description": "The name of the Managed Cluster resource."
            }
        },
        "location": {
            "type": "string",
            "metadata": {
                "description": "The location of AKS resource."
            }
        },
        "dnsPrefix": {
            "type": "string",
            "metadata": {
                "description": "DNS prefix to use with hosted Kubernetes API server FQDN."
            }
        },
        "osDiskSizeGB": {
            "type": "int",
            "defaultValue": 0,
            "metadata": {
                "description": "Disk size (in GiB) to provision for each of the agent pool nodes. This value ranges from 0 to 1023. Specifying 0 will apply the default disk size for that agentVMSize."
            },
            "minValue": 0,
            "maxValue": 1023
        },
        "kubernetesVersion": {
            "type": "string",
            "defaultValue": "1.20.7",
            "metadata": {
                "description": "The version of Kubernetes."
            }
        },
        "networkPlugin": {
            "type": "string",
            "defaultValue": "kubenet",
            "allowedValues": [
                "kubenet"
            ],
            "metadata": {
                "description": "Network plugin used for building Kubernetes network."
            }
        },
        "enableRBAC": {
            "type": "bool",
            "defaultValue": true,
            "metadata": {
                "description": "Boolean flag to turn on and off of RBAC."
            }
        },
        "enablePrivateCluster": {
            "type": "bool",
            "defaultValue": false,
            "metadata": {
                "description": "Enable private network access to the Kubernetes cluster."
            }
        },
        "enableHttpApplicationRouting": {
            "type": "bool",
            "defaultValue": true,
            "metadata": {
                "description": "Boolean flag to turn on and off http application routing."
            }
        },
        "enableAzurePolicy": {
            "type": "bool",
            "defaultValue": false,
            "metadata": {
                "description": "Boolean flag to turn on and off Azure Policy addon."
            }
        }, 
        "nodeSize": {
            "type": "string",
            "defaultValue": "Standard_B4ms",
            "metadata": {
                "description": "Size of the Nodes in the cluster."
            }
        },
        "nodeCount": {
            "type": "int",
            "defaultValue": 1,
            "metadata": {
                "description": "How many nodes to deploy for the cluster."
            },
            "minValue": 1,
            "maxValue": 50
        },
        "inputTags": {
            "type": "object",
            "metadata": {
                "description": "Key value pairs of tags to create on each resource."
            }
        }
    },
    "resources": [
        {
            "apiVersion": "2021-02-01",
            "dependsOn": [],
            "type": "Microsoft.ContainerService/managedClusters",
            "location": "[parameters('location')]",
            "name": "[parameters('resourceName')]",
            "properties": {
                "kubernetesVersion": "[parameters('kubernetesVersion')]",
                "enableRBAC": "[parameters('enableRBAC')]",
                "dnsPrefix": "[parameters('dnsPrefix')]",
                "agentPoolProfiles": [
                    {
                        "name": "agentpool",
                        "osDiskSizeGB": "[parameters('osDiskSizeGB')]",
                        "count": "[parameters('nodeCount')]",
                        "enableAutoScaling": false,
                        "vmSize": "[parameters('nodeSize')]",
                        "osType": "Linux",
                        "storageProfile": "ManagedDisks",
                        "type": "VirtualMachineScaleSets",
                        "mode": "System",
                        "maxPods": 110,
                        "availabilityZones": [],
                        "tags": "[parameters('inputTags')]"
                    }
                ],
                "networkProfile": {
                    "loadBalancerSku": "standard",
                    "networkPlugin": "[parameters('networkPlugin')]"
                },
                "apiServerAccessProfile": {
                    "enablePrivateCluster": "[parameters('enablePrivateCluster')]"
                },
                "addonProfiles": {
                    "httpApplicationRouting": {
                        "enabled": "[parameters('enableHttpApplicationRouting')]"
                    },
                    "azurepolicy": {
                        "enabled": "[parameters('enableAzurePolicy')]"
                    }
                }
            },
            "tags": "[parameters('inputTags')]",
            "identity": {
                "type": "SystemAssigned"
            }
        }
    ],
    "outputs": {
        "controlPlaneFQDN": {
            "type": "string",
            "value": "[reference(concat('Microsoft.ContainerService/managedClusters/', parameters('resourceName'))).fqdn]"
        }
    }
}    
"""


def run(job, **kwargs):
    logger.debug(f"Dictionary of keyword args passed to this "
                 f"plug-in: {kwargs.items()}")
    resource = kwargs.get('resource')
    if resource:
        set_progress(f'Starting deploy of ARM Template for resource: '
                     f'{resource}')
        env_id = "{{env_id}}"
        resource_group = "{{resource_group}}"
        deployment_name = f'{resource.name}-cbdeploy-job-{job.id}'
        if not (env_id and resource_group):
            msg = (f'Required parameter not found. env_id: {env_id}, '
                   f'resource_group: {resource_group}')
            set_progress(msg)
            return "FAILURE", msg, ""

        # Store data about deployment to the resource
        bp_context = kwargs.get('blueprint_context')["aks_cluster_build"]
        for param in bp_context.keys():
            if param == 'service_item_id':
                continue
            if param == '__untrusted_expressions':
                continue
            cf_name = param
            cf_value = bp_context[cf_name]
            cf_type = type(cf_value).__name__.upper()
            cf_label = cf_name.replace('_', ' ').title()
            create_cf(cf_name, cf_label, "", cf_type, show_on_servers=True)
            resource.set_value_for_custom_field(cf_name, cf_value)
            resource.save()

        # Generic ARM Params
        timeout = 900

        # Other Params
        owner = job.owner
        group = resource.group
        env = Environment.objects.get(id=env_id)
        rh = env.resource_handler.cast()

        # Inject Tags
        # Get Tags from Group and Resource Handler. If matching attrs exist on
        # the resource then include them as tags
        tags = rh.taggableattribute_set.all()
        tags_to_apply = {}
        # Grab tags from the Group level first. Only applies params if a single
        # value is set for the group, and the param is required
        for tag in tags:
            tag_attribute = tag.attribute
            tag_name = tag.label
            cfvs = group.get_cfvs_for_custom_field(tag_attribute)
            if cfvs is not None:
                if len(cfvs) == 1:
                    cf = group.custom_fields.get(name=tag_attribute)
                    if cf.required:
                        tag_value = cfvs.first().value
                        if tag_value is not None:
                            tags_to_apply[tag_name] = f'{tag_value}'

        # Then grab tags from the Resource (these would overwrite Group level)
        for tag in tags:
            tag_attribute = tag.attribute
            tag_name = tag.label
            eval_str = f'resource.{tag_attribute}'
            try:
                tag_value = eval(eval_str)
            except AttributeError:
                continue
            if tag_value is not None:
                tags_to_apply[tag_name] = f'{tag_value}'

        # Create Parameter inputs
        params_dict = {
            "resourceName": "{{resource.name}}",
            "location": env.node_location,
            "nodeSize": "{{node_size}}",
            "nodeCount": {{node_count}},
            "osDiskSizeGB": {{os_disk_size}},
            "kubernetesVersion": "{{kubernetes_version}}",
            "dnsPrefix": "{{dns_prefix}}",
            "enableRBAC": {{enable_rbac}},
            "enablePrivateCluster": {{enable_private_cluster}},
            "enableHttpApplicationRouting": {{http_application_routing}},
            "enableAzurePolicy": {{enable_azure_policy}},
            "inputTags": tags_to_apply
        }

        # Get the template from file path
        template = json.loads(get_arm_template())

        # Write the API Versions back to the Resource - to be used on delete
        for template_resource in template["resources"]:
            api_version = template_resource["apiVersion"]
            ms_type = template_resource["type"]
            type_split = ms_type.split('/')
            ms_type_us = ms_type.replace('.', '').replace('/', '_').lower()
            api_version_key = f'{ms_type_us}_api_version'
            # If the API version is already set for an Azure type on the
            # resource, no need to set again, check to see if it exists then
            # set if not present
            try:
                val = resource.get_cfv_for_custom_field(api_version_key).value
                logger.debug(f'Value already set for api_version_key: '
                             f'{api_version_key}, value: {val}')
            except AttributeError:
                api_key_name = f'{type_split[-1]} API Version'
                logger.debug(f'Creating CF: {api_version_key}')
                create_cf(api_version_key, api_key_name, (
                    f'The API Version that {ms_type} '
                    f'resources were provisioned with in this deployment')
                )
                resource.set_value_for_custom_field(api_version_key,
                                                    api_version)
            except NameError:
                resource.set_value_for_custom_field(api_version_key,
                                                    api_version)

        # Submit the template request
        if timeout:
            timeout = int(timeout)
        else:
            timeout = 3600
        wrapper = rh.get_api_wrapper()
        logger.debug(f'Submitting request for ARM template. deployment_name: '
                     f'{deployment_name}, resource_group: {resource_group}, '
                     f'template: {template}')
        set_progress(f'Submitting ARM request to Azure. This can take a while.'
                     f' Timeout is set to: {timeout}')
        deployment = wrapper.deploy_template(deployment_name, resource_group,
                                             template, params_dict,
                                             timeout=timeout)
        set_progress(f'Deployment created successfully')
        logger.debug(f'deployment info: {deployment}')
        get_or_create_cfs()
        deploy_props = deployment.properties
        logger.debug(f'deployment properties: {deploy_props}')
        resource.azure_rh_id = rh.id
        resource.azure_region = env.node_location
        resource.azure_deployment_id = deployment.id
        resource.azure_correlation_id = deploy_props.correlation_id
        resource.resource_group = resource_group
        i = 0
        for output_resource in deploy_props.additional_properties[
            "outputResources"]:
            id_value = output_resource["id"]
            type_value = id_value.split('/')[-2]

            # If a server, create the CloudBolt Server object
            if type_value == 'virtualMachines':
                resource_client = wrapper.resource_client
                api_version_key = get_api_version_key_from_id(id_value)
                api_version = resource.get_cfv_for_custom_field(
                    api_version_key).value
                vm = resource_client.resources.get_by_id(id_value,
                                                         api_version)
                vm_dict = vm.__dict__
                svr_id = vm_dict["properties"]["vmId"]
                location = vm_dict["location"]
                node_size = vm_dict["properties"]["hardwareProfile"]["vmSize"]
                disk_ids = [vm_dict["properties"]["storageProfile"]["osDisk"]
                            ["managedDisk"]["id"]]
                for disk in vm_dict["properties"]["storageProfile"]\
                        ["dataDisks"]:
                    disk_ids.append(disk["managedDisk"]["id"])
                if svr_id:
                    # Server manager does not have the create_or_update method,
                    # so we do this manually.
                    try:
                        server = Server.objects.get(
                            resource_handler_svr_id=svr_id)
                        server.resource = resource
                        server.group = group
                        server.owner = resource.owner
                        server.environment = env
                        server.save()
                        logger.info(
                            f"Found existing server record: '{server}'")
                    except Server.DoesNotExist:
                        logger.info(
                            f"Creating new server with resource_handler_svr_id "
                            f"'{svr_id}', resource '{resource}', group '{group}', "
                            f"owner '{resource.owner}', and "
                            f"environment '{env}'"
                        )
                        server_name = get_azure_server_name(id_value)
                        server = Server(
                            hostname=server_name,
                            resource_handler_svr_id=svr_id,
                            resource=resource,
                            group=group,
                            owner=resource.owner,
                            environment=env,
                            resource_handler=rh
                        )
                        server.save()
                        server.resource_group = resource_group
                        server.save()

                        tech_dict = {
                            "location": location,
                            "resource_group": resource_group,
                            "storage_account": None,
                            "extensions": [],
                            "availability_set": None,
                            "node_size": node_size,
                        }
                        rh.update_tech_specific_server_details(server,
                                                               tech_dict, None)
                        server.refresh_info()
                    # Add server to the job.server_set, and set creation event
                    job.server_set.add(server)
                    job.save()
                    msg = "Server created by ARM Template job"
                    add_server_event("CREATION", server, msg,
                                     profile=job.owner, job=job)
                    api_version_key = get_api_version_key_from_id(disk_ids[0])
                    api_key_name = f"{api_version_key.split('_')[1]} API Version"
                    create_cf(api_version_key, api_key_name, (
                        f'The API Version that Microsoft.Compute/disks '
                        f'resources were provisioned with in this deployment')
                              )
                    # Write the api_version for Virtual Machine to the disk
                    # value
                    resource.set_value_for_custom_field(api_version_key,
                                                        '2021-04-01')
                    for disk_id in disk_ids:
                        field_name_id = f'output_resource_{i}_id'
                        resource = create_field_set_value(field_name_id,
                                                          disk_id, i, resource)
                        i += 1
                        resource.save()
            field_name_id = f'output_resource_{i}_id'
            resource = create_field_set_value(field_name_id, id_value, i,
                                              resource)
            i += 1
            resource.save()
        return "SUCCESS", "ARM Template deployment complete", ""
    else:
        msg = f'Resource not found.'
        set_progress(msg)
        return "FAILURE", msg, ""


if __name__ == "__main__":
    job_id = sys.argv[1]
    j = Job.objects.get(id=job_id)
    run = run(j)
    if run[0] == "FAILURE":
        set_progress(run[1])
