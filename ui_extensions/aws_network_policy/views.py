import json

from django.shortcuts import render

import settings
from extensions.views import tab_extension, TabExtensionDelegate
from infrastructure.models import Server
from resourcehandlers.aws.models import AWSHandler
from resourcehandlers.models import ResourceHandler
from utilities.decorators import json_view


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
    context = {
        'rh_id': obj_id
    }
    return render(request, 'aws_network_policy/templates/resourcehandler_tab.html', context=context)


@tab_extension(model=Server, title='Security Hub', delegate=AWSSecurityHubServerTabDelegate)
def server_tab(request, obj_id):
    context = {
        'server_id': obj_id
    }
    return render(request, 'aws_network_policy/templates/server_tab.html', context=context)


@json_view
def aws_network_policy_server_json(request, server_id):
    server = Server.objects.get(id=server_id)
    response = json.loads(server.aws_securityhub_findings)
    findings = []

    for finding in response:
        row = [
            finding['Title'],
            finding['Description'],
            finding['Remediation']['Recommendation']['Text'],
            finding['Severity']['Product'],
            finding['Severity']['Normalized'],
        ]
        findings.append(row)

    return {
        # unaltered from client-side value, but cast to int to avoid XSS
        # http://datatables.net/usage/server-side
        "sEcho": int(request.GET.get('sEcho', 1)),
        "iTotalRecords": 10,
        "iTotalDisplayRecords": 10,
        'aaData': findings,
    }


@json_view
def aws_network_policy_rh_json(request, rh_id):
    server = Server.objects.get(id=rh_id)
    # response = json.loads(server.aws_securityhub_findings)
    response = []
    findings = []

    for finding in response:
        row = [finding['Title'], finding['Description'], finding['Remediation']['Recommendation']['Text']]
        findings.append(row)

    return {
        # unaltered from client-side value, but cast to int to avoid XSS
        # http://datatables.net/usage/server-side
        "sEcho": int(request.GET.get('sEcho', 1)),
        "iTotalRecords": 10,
        "iTotalDisplayRecords": 10,
        'aaData': findings,
    }
