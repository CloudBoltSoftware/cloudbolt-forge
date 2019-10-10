import json

from django.shortcuts import render

import settings
from extensions.views import tab_extension, TabExtensionDelegate
from infrastructure.models import Server
from resourcehandlers.aws.models import AWSHandler
from resourcehandlers.models import ResourceHandler


class AWSSecurityHubResourceHandlerTabDelegate(TabExtensionDelegate):
    def should_display(self):
        rh: ResourceHandler = self.instance
        return isinstance(rh.cast(), AWSHandler)


class AWSSecurityHubServerTabDelegate(TabExtensionDelegate):
    def should_display(self):
        server: Server = self.instance
        return server.get_value_for_custom_field('aws_securityhub_findings') is not None


@tab_extension(model=ResourceHandler, title='Security Hub', delegate=AWSSecurityHubResourceHandlerTabDelegate)
def resourcehandler_tab(request, obj_id):
    rh = ResourceHandler.objects.get(id=obj_id)
    with open(settings.PROSERV_DIR + '/findings.json', "r") as f:
        findings = json.load(f)
    context = {
        'findings_by_type': findings
    }
    return render(request, 'aws_network_policy/templates/resourcehandler_tab.html', context=context)


@tab_extension(model=Server, title='Security Hub', delegate=AWSSecurityHubServerTabDelegate)
def server_tab(request, obj_id):
    server = Server.objects.get(id=obj_id)
    context = {
        'findings': json.loads(server.aws_securityhub_findings)
    }
    return render(request, 'aws_network_policy/templates/server_tab.html', context=context)
