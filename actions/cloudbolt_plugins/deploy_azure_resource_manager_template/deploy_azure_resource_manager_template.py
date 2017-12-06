#!/usr/local/bin/python2.7

from common.methods import set_progress
from infrastructure.models import Server
from servicecatalog.models import ServiceItem
from utilities.events import add_service_event, add_server_event
from resourcehandlers.azure_arm.models import AzureARMHandler

"""
This is an example of building resources defined in a given Azure Resource Manager template.
Run this plugin as a Service Action to build the resources defined in the template provided.

The parameters dict is a simple wrapper that lists all parameters defined in the template. Some of those
parameters can be exposed as action inputs, while others could be hard-coded here in this plugin,
depending on how this template might be deployed.

The template dir could be converted to accept an action input, which would convert this plugin to
be able to run any ARM template. But since various parameters are required by different templates,
writing a plugin to wrap each template is probably required.

The example template dir used here comes from https://github.com/Azure/azure-quickstart-templates
That repo lists dozens of ARM templates, any of which should be compatible with this plugin.

To convert this plugin for another template:

1) Copy the template, including the parent directory, to the CloudBolt server
2) Change the template_dir to reflect the path to the new template dir.
3) Change the 'parameters' dict to include keys for all the parameters listed in the template.
4) For each parameter value, provide either a value or a variable reference (to be converted to
    an action input) 
5) Adjust timeout (default is 1 hour)
"""


def run(job, logger=None, **kwargs):
    params = job.job_parameters.cast()
    service = params.services.first()
    
    deployment_name = "{{name}}"
    resource_group = "{{resource_group}}"
    
    parameters = {
        'adminUsername': '{{adminUsername}}',
        'adminPassword': '{{adminPassword}}',
        'dnsLabelPrefix': '{{dnsLabelPrefix}}',
        'ubuntuOSVersion': "16.04.0-LTS",
    }
    handler = AzureARMHandler.objects.first()
    template_dir = '/var/opt/cloudbolt/proserv/arm_templates/101-vm-simple-linux/'

    timeout = '{{timeout}}'
    if timeout:
      timeout = int(timeout)
    else:
      timeout = 3600
    try:
      handler.deploy_arm_template(deployment_name, resource_group, template_dir, parameters, timeout)
    except:
      handler.deploy_arm_template(deployment_name, resource_group, template_dir, parameters)
      # Timeout kwarg was added in CloudBolt 7.7    
    
    return "", "", ""


if __name__ == '__main__':
    from utilities.logger import ThreadLogger
    logger = ThreadLogger(__name__)
    print(run(None, logger))