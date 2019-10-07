import boto3

from django.shortcuts import render

from extensions.views import tab_extension, TabExtensionDelegate
from resourcehandlers.models import ResourceHandler
from resourcehandlers.aws.models import AWSHandler


class NetworkFlowTabDelegate(TabExtensionDelegate):
    def should_display(self, **kwargs):
        # TODO: only display for AWS, but kwargs is empty :(
        print("kwargs:", kwargs)
        return True


@tab_extension(model=ResourceHandler, title='Net Flow', delegate=NetworkFlowTabDelegate)
def network_flow_tab(request, obj_id):
    rh = AWSHandler.objects.get(id=obj_id)
    events = get_logs(rh)

    return render(request, 'aws_network_flow/templates/network_flow.html', context={
        "handler": rh,
        "events": events,
    })


def get_logs(rh):
    group_name = ""
    client = boto3.client(
        'logs',
        region_name='us-east-1',  # region must be us-east-1; data from all regions is sent there.
        aws_access_key_id=rh.serviceaccount,
        aws_secret_access_key=rh.servicepasswd
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
        # the fields in each event are:
        # version account_id interface_id srcaddr dstaddr srcport dstport protocol packets bytes start end action log_status
        msgparts = event['message'].split(" ")[2:]  # skip the version & account ID, they're not useful
        row = [event['logStreamName'], event['timestamp']]
        row.extend(msgparts)
        events.append(row)

    return events
