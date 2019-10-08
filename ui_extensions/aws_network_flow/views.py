import boto3
import json

from django.shortcuts import render

from extensions.views import tab_extension, TabExtensionDelegate
from resourcehandlers.models import ResourceHandler
from resourcehandlers.aws.models import AWSHandler
from utilities.decorators import json_view


class NetworkFlowTabDelegate(TabExtensionDelegate):
    def should_display(self, **kwargs):
        # TODO: only display for AWS, but kwargs is empty :(
        print("kwargs:", kwargs)
        return True


@tab_extension(model=ResourceHandler, title='Net Flow', delegate=NetworkFlowTabDelegate)
def network_flow_tab(request, obj_id):
    handler = AWSHandler.objects.get(id=obj_id)
    return render(request, 'aws_network_flow/templates/network_flow.html', context={"handler": handler})


@json_view
def aws_net_flows_json(request, handler_id):
    handler = AWSHandler.objects.get(id=handler_id)

    group_name = ""
    client = boto3.client(
        'logs',
        region_name='us-east-1',  # region must be us-east-1; data from all regions is sent there.
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd
    )
    response = client.filter_log_events(
        logGroupName=group_name,
        logStreamNames=[
            '',
        ],
        limit=10,
        interleaved=True,
    )
    events = []
    for event in response['events']:
        # The fields in each event are:
        # version account_id interface_id srcaddr dstaddr srcport dstport protocol packets bytes start end action log_status
        msgparts = event['message'].split(" ")[2:]  # skip the version & account ID, they're not useful
        row = [event['logStreamName'], event['timestamp']]
        row.extend(msgparts)
        events.append(row)

    return {
        # unaltered from client-side value, but cast to int to avoid XSS
        # http://datatables.net/usage/server-side
        "sEcho": int(request.GET.get('sEcho', 1)),
        "iTotalRecords": 10,
        "iTotalDisplayRecords": 10,
        'aaData': events,
    }
