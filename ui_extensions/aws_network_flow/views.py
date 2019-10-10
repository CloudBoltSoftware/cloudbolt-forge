import datetime
import json
import socket

import boto3

from django.shortcuts import render

from extensions.views import tab_extension, TabExtensionDelegate
from resourcehandlers.models import ResourceHandler
from resourcehandlers.aws.models import AWSHandler
from utilities.decorators import json_view
from utilities.templatetags import helper_tags

from .forms import AWSNetFlowFilterForm

from settings import AWS_NET_FLOW_LOG_GROUP_NAME, AWS_NET_FLOW_LOG_STREAM_NAMES

PROTOCOL_TABLE = {num: name[8:] for name, num in vars(socket).items() if name.startswith("IPPROTO")}
EPOCH = datetime.datetime.utcfromtimestamp(0)


class NetworkFlowTabDelegate(TabExtensionDelegate):
    def should_display(self, **kwargs):
        # Only display for AWS
        handler = self.instance
        if handler.resource_technology.type_slug != "aws":
            return False
        return True


def _get_boto_logs_client(handler):
    return boto3.client(
        'logs',
        region_name='us-east-1',  # region must be us-east-1; data from all regions is sent there.
        aws_access_key_id=handler.serviceaccount,
        aws_secret_access_key=handler.servicepasswd
    )


@tab_extension(model=ResourceHandler, title='Net Flow', delegate=NetworkFlowTabDelegate)
def network_flow_tab(request, obj_id):
    handler = AWSHandler.objects.get(id=obj_id)

    return render(request, 'aws_network_flow/templates/network_flow.html', context={
        "handler": handler,
    })


def _parse_date_to_ms_since_epoch(date):
    """
    Tries to parse the incoming dates from specific format,
    returns None for exceptions
    else returns the milliseconds since epoch as an int
    """
    try:
        # Incoming date format is defined by the bootstrap-datepicker's 'format' keyword in c2/datepicker.js
        parsed_date = datetime.datetime.strptime(date, u'%m-%d-%Y')
    except (ValueError, IndexError):
        return 0
    else:
        return int((parsed_date - EPOCH).total_seconds() * 1000)


def _load_filters_from_get_params(request):
    """
    Processes the HTTP GET request for filters selected and calls json.loads as a workaround
    for de-serialization issues.
    Returns a dict of filters by field.
    """
    # json for all of the filters selected on the form.
    filters_selected = json.loads(request.GET.get('filters_selected', '{}'))
    print(f"filters_selected: {filters_selected}")
    filters = {}

    for field_name in filters_selected:
        if field_name == 'new_filters':
            continue

        val = filters_selected.get(field_name)
        if val and val[0]:
            if field_name.endswith("Time"):
                filters[field_name] = _parse_date_to_ms_since_epoch(filters_selected[field_name][0])
            else:
                filters[field_name] = filters_selected[field_name][0]
    return filters



@json_view
def aws_net_flows_json(request, handler_id):
    handler = AWSHandler.objects.get(id=handler_id)
    limit = int(request.GET.get('iDisplayLength', 25))
    filters = _load_filters_from_get_params(request)

    client = _get_boto_logs_client(handler)
    response = client.filter_log_events(
        logGroupName=AWS_NET_FLOW_LOG_GROUP_NAME,
        logStreamNames=AWS_NET_FLOW_LOG_STREAM_NAMES,
        limit=limit,
        interleaved=True,
        **filters
    )
    events = []
    for event in response['events']:
        # The fields in each event are:
        # version account_id interface_id srcaddr dstaddr srcport dstport protocol packets bytes start end action log_status
        msg_parts = event['message'].split(" ")[2:]  # skip the version & account ID, they're not useful
        event_time = datetime.datetime.fromtimestamp(event['timestamp']/1000)
        row = [helper_tags.when(event_time)]

        # Try to convert the protocol # to a name. If not found in the lookup table, fall back to the protocol #
        protocol_index = 5
        if msg_parts[protocol_index].isdigit():
            msg_parts[protocol_index] = PROTOCOL_TABLE.get(int(msg_parts[protocol_index]), msg_parts[protocol_index])

        row.extend(msg_parts)
        events.append(row)

    return {
        # Unaltered from client-side value, but cast to int to avoid XSS http://datatables.net/usage/server-side
        "sEcho": int(request.GET.get('sEcho', 1)),
        "iTotalRecords": len(events),
        "iTotalDisplayRecords": limit,
        'aaData': events,
    }


def filter_form(request, handler_id):
    """
    Return the HTML for the AWS net flow filter form.

    This is called via AJAX when a user clicks on the "Show Filters" button for the first time.
    """
    if request.method == 'POST':
        filters_form = AWSNetFlowFilterForm(request.POST)
        if filters_form.is_valid():
            return
    else:
        filters_form = AWSNetFlowFilterForm(dict())

    context = {'filters_form': filters_form}

    return render(request, 'aws_network_flow/templates/filter_form.html', context)
