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

from settings import AWS_NET_FLOW_LOG_GROUP_NAME

PROTOCOL_TABLE = {num: name[8:] for name, num in vars(socket).items() if name.startswith("IPPROTO")}
EPOCH = datetime.datetime.utcfromtimestamp(0)

# Setting this to True will cause this extension to not call into AWS to get data. Useful for working on UI
# changes that do not need real data from AWS to test.
DEBUG_MODE = False


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
    filters = {}

    # Whatever is passed by the client in filters_selected, just return that to be passed that along as arguments to
    # filter_log_events()
    for field_name in filters_selected:
        if field_name == 'new_filters':
            continue

        val = filters_selected.get(field_name)
        if val and val[0]:
            if field_name.endswith("Time"):
                filters[field_name] = _parse_date_to_ms_since_epoch(filters_selected[field_name][0])
            elif field_name == 'logStreamNames':
                # Leave the multi-value filter as a list
                filters[field_name] = filters_selected[field_name]
            else:
                # Flatten single-item lists to scalar values
                filters[field_name] = filters_selected[field_name][0]
    return filters


@json_view
def aws_net_flows_json(request, handler_id):
    handler = AWSHandler.objects.get(id=handler_id)
    limit = int(request.GET.get('iDisplayLength', 25))
    filters = _load_filters_from_get_params(request)

    client = _get_boto_logs_client(handler)
    if DEBUG_MODE:
        response = {
            'events': [
                {'logStreamName': 'eni-059991d290dd409db-accept', 'timestamp': 1570041981000,
                 'message': '2 548575475449 eni-059991d290dd509db 10.110.0.88 45.77.78.241 60373 123 17 1 76 1570041981 1570042039 ACCEPT OK',
                 'ingestionTime': 1570042481642, 'eventId': 'FAKE'}],
            'searchedLogStreams': [{'logStreamName': 'eni-028774ec409393468-accept', 'searchedCompletely': False}],
            'nextToken': 'FAKE',
            'ResponseMetadata': {'RequestId': 'FAKE', 'HTTPStatusCode': 200,
                                 'HTTPHeaders': {
                                     'x-amzn-requestid': 'FAKE', 'content-type': 'application/x-amz-json-1.1',
                                     'content-length': '2134', 'date': 'Fri, 11 Oct 2019 15:43:18 GMT'},
                                 'RetryAttempts': 0}
        }
    else:
        response = client.filter_log_events(
            logGroupName=AWS_NET_FLOW_LOG_GROUP_NAME,
            limit=limit,
            interleaved=True,
            **filters
        )

    events = []
    for event in response['events']:
        # The fields in each event are:
        # version account_id interface_id srcaddr dstaddr srcport dstport protocol packets bytes start end
        # action log_status
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
        # TODO change these next two to enable pagination- somehow figure out the total # of records
        "iTotalRecords": len(events),
        "iTotalDisplayRecords": limit,
        'aaData': events,
    }


def _get_log_stream_names(handler):
    if DEBUG_MODE:
        return ['eni-028774ec45639346a-accept', 'eni-058991d130ad509db-accept']
    else:
        client = _get_boto_logs_client(handler)
        response = client.describe_log_streams(logGroupName=AWS_NET_FLOW_LOG_GROUP_NAME)['logStreams']
        return [log_stream['logStreamName'] for log_stream in response]


def filter_form(request, handler_id):
    """
    Return the HTML for the AWS net flow filter form.

    This is called via AJAX when a user clicks on the "Show Filters" button for the first time.
    """
    handler = AWSHandler.objects.get(id=handler_id)
    stream_options = _get_log_stream_names(handler)

    if request.method == 'POST':
        filters_form = AWSNetFlowFilterForm(request.POST, stream_options=stream_options)
        if filters_form.is_valid():
            return
    else:
        filters_form = AWSNetFlowFilterForm(dict(), stream_options=stream_options)

    context = {'filters_form': filters_form}

    return render(request, 'aws_network_flow/templates/filter_form.html', context)
