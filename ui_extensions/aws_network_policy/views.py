import json

from django.shortcuts import render

from extensions.views import tab_extension, TabExtensionDelegate
from infrastructure.models import Server
from utilities.decorators import json_view


class AWSInspectorServerTabDelegate(TabExtensionDelegate):
    def should_display(self):
        server: Server = self.instance
        return server.get_value_for_custom_field('aws_inspector_findings') is not None


@tab_extension(model=Server, title='Inspector', delegate=AWSInspectorServerTabDelegate)
def server_tab(request, obj_id):
    context = {
        'server_id': obj_id
    }
    return render(request, 'aws_network_policy/templates/server_tab.html', context=context)


@json_view
def aws_network_policy_server_json(request, server_id):
    server = Server.objects.get(id=server_id)
    response = json.loads(server.aws_inspector_findings)
    findings = []

    for finding in response:
        row = [
            finding['title'],
            finding['description'],
            finding['recommendation'],
            finding['severity'],
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
