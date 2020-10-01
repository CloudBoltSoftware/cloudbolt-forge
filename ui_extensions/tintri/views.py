"""
Provides features to support a Tintri storage array.

Servers in environments that have a Tintri store will have a "Tintri" tab on
their detail view. This tab exposes storage performance metrics as well as some
actions users can take on the server, such as taking a snapshot.
"""
import os
import datetime
import json
import time
import logging
from dateutil import parser

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext as _

from cbhooks.views import _format_action_html_response
from extensions.views import admin_extension, tab_extension, TabExtensionDelegate
from infrastructure.models import Server
from resourcehandlers.vmware.models import VsphereResourceHandler
from tabs.views import TabGroup
from utilities.decorators import dialog_view
from utilities.exceptions import CloudBoltException
from utilities.logger import ThreadLogger
from utilities.permissions import cbadmin_required
from utilities.templatetags import helper_tags
from xui.tintri.forms import TintriCloneSnapshotForm, TintriEndpointForm, TintriSnapshotForm
from xui.tintri.tintri_api import Tintri

logger = ThreadLogger(__name__)

"""
UI Extension view using Tintri rest API
"""

COLOR1 = '#2A17B1'
COLOR2 = '#FF9E00'
COLOR3 = '#00A67C'


def get_ci(server):
    tintri = Tintri()
    ci = tintri.get_connection_info()
    if not ci:
        return None
    t = {}
    t['ip'] = ci.ip
    t['username'] = ci.username
    t['password'] = ci.password
    return t


def get_session(server):
    """
    Get authenticated Tintri Session for the given server

    Requires:
        ConnectionInfo object with name 'Tintri VMstore for Environment X'
        Otherwise return None

    Args:
        server (obj): CB server object

    Returns:
        tintri: Tintri object
    """
    # instantiate the Tintri server.
    tintri = Tintri()
    tintri.get_session_id(None, save_to_self=True)
    # Login to VMstore
    conn = tintri.get_connection_info()
    if not conn:
        return None
    return tintri


def get_appliance_info(tintri):
    """
    Get Tintri Appliance details

    Args:
        tintri (obj): Tintri object

    Returns:
        appliance: Dict of apliance details
    """
    appliance = {}
    info = tintri.get_appliance_info()
    product = None
    if tintri.is_vmstore():
        product = 'Tintri VMstore'
    elif tintri.is_tgc():
        product = 'Tintri Global Center'
    appliance['product'] = product
    appliance['model'] = info.get('modelName')
    return appliance


def get_vm(tintri, server, save_to_server=True):
    """
    Get Tintri Virtual Machine object by VM name

    Args:
        tintri  (obj): Tintri object with session_id
        server (Server): The CloudBolt Server object
        save_to_server: bool.  If not in the server save it as tintri_vm_uuid

    Returns:
        vm
    # """
    # vm_filter_spec = VirtualMachineFilterSpec()
    vm_name = server.get_vm_name()
    logging.info('Requesting VM details from Tintri for VM: "{}"'.format(vm_name))

    if server.tintri_vm_uuid:
        tintri_vm = tintri.get_vm_by_uuid(server.tintri_vm_uuid)
    else:
        tintri_vm = tintri.get_vm_by_name(vm_name)

    vm = {}
    vm["name"] = tintri_vm.get("vmware").get("name")
    vm["uuid"] = tintri_vm.get("uuid").get("uuid")
    vm['maxNormalizedIops'] = tintri_vm.get("qosConfig").get("maxNormalizedIops")

    logging.info(f"Found Tintri VM with Name: {vm.get('name')} and UUID: {vm.get('uuid')}")

    if save_to_server:
        server.tintri_vm_uuid = vm.get("uuid", None)

    return vm


def get_vm_stats(tintri, vm_uuid, days):
    '''
    Get all Tintri Virtual Machine stats for the past X days (from now)

    Args:
        tintri  (obj): Tintri object with session_id
        vm_uuid (str): Virtual Machine's UUID
        days    (int): Total days of stats

    Returns:
        sorted_stats: [] of sorted stats
    '''
    # vm_stats_filter_spec = VirtualMachineFilterSpec()
    # Specify date range for stats
    # The end date in ISO8601 format - 'YYYY-MM-DDThh:mm:ss.ms-/+zz:zz'
    until = datetime.datetime.now()
    since = until - datetime.timedelta(days=days)
    until = until.isoformat()[:-3] + '-00:00'
    since = since.isoformat()[:-3] + '-00:00'

    results = tintri.get_vm_historic_stats(uuid=vm_uuid, since=since, until=until)

    sorted_stats = results.get('items')[0].get('sortedStats')

    return sorted_stats


def get_chart_plotline(vm_stats, attr, name, color):
    '''
    Generate chart dictionary for highcharts graph

    Args:
        vm_stats (obj): Results of get_vm_stats
        attr     (str): Attr of stats object for chart
        name     (str): Name of the chart
        color    (str): Line color of chart

    Returns:
        chart: {} Chart data for highcharts graph
    '''
    data = []
    for stat in vm_stats:
        a = stat.get(attr)
        date = parser.parse(stat.get('timeEnd'))
        timestamp = int(time.mktime(date.utctimetuple())) * 1000
        result = [timestamp, a]
        data.append(result)
    plot = {
        'data': data,
        'name': name,
        'color': color,
        'type': "area"
    }
    return plot



class TintriTabDelegate(TabExtensionDelegate):

    def should_display(self):
        if self.instance.resource_handler:
            return isinstance(self.instance.resource_handler.cast(), VsphereResourceHandler)

        return False


def dict_to_vmstat(statdict):
    vmstat = VirtualMachineStat()
    for k, v in statdict.items():
        setattr(vmstat, k, v)
    return vmstat


@tab_extension(model=Server,
               title='Tintri Metrics',
               description='Tintri Metrics Tab',
               delegate=TintriTabDelegate)
def server_metrics_tintri(request, obj_id=None):
    """
    Tintri Server Tab Extension
    Requires:
        Install Tintri PySDK
        ConnectionInfo object with name 'tintri'
        VCenter cluster with Tintri VMStore
    """
    server = get_object_or_404(Server, pk=obj_id)
    vm_name = server.get_vm_name()
    appliance_info = {
        'product': 'Tintri VMstore',
        'model': 'T5000'
    }

    if server.tags.filter(name='demdo'):
        mydir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(mydir, 'demo.json')) as data_file:
            # When using the demo JSON, to get the graphs to appear, the 'time' and 'endTime'
            # values need to be updated to be within the last day. TODO: automate this here
            vm_stat_dicts = json.load(data_file)
            vm_stats = []
            for statdict in vm_stat_dicts:
                vm_stats.append(dict_to_vmstat(statdict))

        maxNormalizedIops = 1000

    else:
        no_vm_message = None

        # get real stats from Tintri
        vm = None
        error = None
        try:
            tintri = get_session(server)
            appliance_info = get_appliance_info(tintri)
            vm = get_vm(tintri, server, save_to_server=True)
        except CloudBoltException as e:
            error = str(e)

        if vm:
            vm_stats = get_vm_stats(tintri, server.tintri_vm_uuid, days=1)
            sorted_stats = vm_stats[-1]

            latency = [
                get_chart_plotline(vm_stats,
                           attr='latencyNetworkMs',
                           name='Network',
                           color=COLOR1),
                get_chart_plotline(vm_stats,
                           attr='latencyHostMs',
                           name='Host',
                           color=COLOR2),
                get_chart_plotline(vm_stats,
                           attr='latencyDiskMs',
                           name='Storage',
                           color=COLOR3),
            ]
            iops = [
                get_chart_plotline(vm_stats,
                           attr='normalizedTotalIops',
                           name='Total',
                           color=COLOR1),
            ]
            throughput = [
                get_chart_plotline(vm_stats,
                           attr='throughputReadMBps',
                           name='Read',
                           color=COLOR3),
                get_chart_plotline(vm_stats,
                           attr='throughputWriteMBps',
                           name='Write',
                           color=COLOR2),
            ]
            maxNormalizedIops = vm.get('maxNormalizedIops')
        else:
            status = 'warning'
            msg = 'Could not find server \'{}\' in the Tintri Appliance '.format(vm_name)
            if error:
                status = "danger"  # make sure the message is red
                msg = f"Error finding server '{vm_name}': {error}"
            maxNormalizedIops = 0
            no_vm_message = helper_tags.alert(status, msg)
            sorted_stats = {
                'spaceUsedGiB': 0, 'spaceProvisionedGiB': 0, 'spaceUsedChangeGiB': 0
            }
            iops = []
            throughput = []
            latency = []



    tintri_data = {
        "disk_used": format(sorted_stats.get('spaceUsedGiB'),
                            '.1f'),
        "disk_provisioned": format(sorted_stats.get('spaceProvisionedGiB'),
                                   '.1f'),
        "disk_changed": format(sorted_stats.get('spaceUsedChangeGiB'),
                               '.1f'),
        "chart_latency": latency,
        "chart_iops": iops,
        "max_iops": maxNormalizedIops,
        "chart_throughput": throughput,
        "max_line_color": "red",
    }

    return render(
        request, 'tintri/templates/server_metrics.html', dict(
            appliance_info=appliance_info,
            tintri_data=tintri_data,
            server=server,
            connection_info=get_ci(server),
            no_vm_message=no_vm_message
        )
    )

def epoch_ms_to_html(epoch_ms):
    from django.utils.html import format_html
    from utilities.templatetags.helper_tags import when
    if epoch_ms < 0:
        return format_html("<i>Never</i>")
    else:
        from datetime import datetime
        return when(datetime.fromtimestamp(epoch_ms/1000))


@tab_extension(model=Server,
               title='Tintri Snapshots',
               description='Tintri Snapshots Tab',
               delegate=TintriTabDelegate)
def server_snapshots_tintri(request, obj_id=None):
    """
    Tintri Server Tab Extension
    Requires:
        Install Tintri PySDK
        ConnectionInfo object with name 'tintri'
        VCenter cluster with Tintri VMStore
    """
    server = get_object_or_404(Server, pk=obj_id)

    appliance_info = {
        'product': 'Tintri VMstore',
        'model': 'T5000'
    }

    no_vm_message = None
    can_manage_snapshots = False

    vm = None
    error = None
    try:
        tintri = get_session(server)
        appliance_info = get_appliance_info(tintri)
        vm = get_vm
    except CloudBoltException as e:
        error = str(e)


    if vm:
        profile = request.get_user_profile()
        can_manage_snapshots = profile.has_permission("server.manage_snapshots", server)

        snapshots = tintri.get_snapshots(f"vmUuid={server.tintri_vm_uuid}")
        for snap in snapshots:
            snap["created_as_html"] = epoch_ms_to_html(snap["createTime"])
            snap["expire_as_html"] = epoch_ms_to_html(snap["expirationTime"])
    else:
        status = 'warning'
        msg = 'Could not find server \'{}\' in the Tintri Appliance '.format(vm_name)
        if error:
            status = "danger"  # make sure the message is red
            msg = f"Error finding server '{vm_name}': {error}"
        no_vm_message = helper_tags.alert(status, msg)


    return render(
        request, 'tintri/templates/server_snapshots.html', dict(
            server=server,
            snapshots=snapshots,
            can_manage_snapshots=can_manage_snapshots,
            no_vm_message=no_vm_message
        )
    )

@dialog_view
@cbadmin_required
def edit_tintri_endpoint(request, endpoint_id=None):
    """
    Create and edit dialog for a Tintri Appliance endpoint.
    If `endpoint_id` is None, creates a new one
    """
    endpoint = Tintri().get_connection_info()
    action_url = reverse('create_tintri_endpoint')
    if endpoint or endpoint_id:
        action_url = reverse('edit_tintri_endpoint', args=[endpoint.id])
    if request.method == 'POST':
        form = TintriEndpointForm(request.POST, instance=endpoint)
        if form.is_valid():
            form.save()
            msg = "The Tintri Appliance Endpoint settings have been saved."
            messages.success(request, msg)
            profile = request.get_user_profile()
            logger.info("Endpoint set to {} by {}.".format(endpoint, profile.user.username))
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = TintriEndpointForm(instance=endpoint)

    return {
        'title': "Modify Tintri Appliance's Endpoint Settings",
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "Tintri Appliance Endpoint, Used to support advanced server metrics and actions",
        'submit': 'Save',
    }

@dialog_view
@cbadmin_required
def delete_tintri_endpoint(request):
    endpoint = Tintri().get_connection_info()
    if request.method == 'POST':
        endpoint.delete()
        msg = "The Tintri Appliance's Endpoint has been deleted."
        messages.success(request, msg)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    return {
        'title': "Remove Tintri Appliance's Endpoint?",
        'content': 'Are you sure you want to delete Tintri Appliance\'s endpoint \'{}\'?'.format(endpoint),
        'use_ajax': True,
        'action_url': reverse('delete_tintri_endpoint'),
        'submit': 'Remove'
    }


@dialog_view
@cbadmin_required
def verify_tintri_endpoint(request):
    tintri = Tintri()
    endpoint = tintri.get_connection_info()
    if not endpoint:
        messages.warn(
            request, "No Tintri Connection Endpoint found! Nothing to verify")
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    try:
        tintri.verify_connection()
    except Exception as err:
        status = 'danger'
        msg = format_html('Could not make a connection to the Tintri Appliance '
                          '<b>"{}"</b>:<br>{}', endpoint, str(err))
    else:
        status = 'success'
        msg = format_html('Successfully connected to the Tintri Appliance at '
                          '<b>"{}"</b>.', endpoint)
    # The alert helper tag will escape the state and msg if they aren't properly
    # marked safe (after any necessary escaping with format_html) here
    content = helper_tags.alert(status, msg)

    return {
        'title': "Verify connection to Tintri Appliance's Connection Endpoint",
        'content': content,
        'submit': None,
        'cancel': "OK",
    }


@admin_extension(title='Tintri Integration', description='Set-up appliance connection, manage hypervisors, etc')
def admin_page(request):
    tintri = Tintri()

    tintri_context = {

        'tabs': TabGroup(
            template_dir='tintri/templates',
            context={
                "endpoint": tintri.get_connection_info(),
                "clone_from_snapshot": tintri.get_or_create_clone_from_snapshot_server_action(),
                "take_snapshot": tintri.get_or_create_take_snapshot_server_action(),
                "delete_snapshot": tintri.get_or_create_delete_snapshot_server_action()
            },
            request=request,
            tabs=[
                # First tab uses template 'groups/tabs/tab-main.html'
                #(_("Configuration"), 'configuration', {}),

                # Tab 2 is conditionally-shown in this slot and
                # uses template 'groups/tabs/tab-related-items.html'
                (_("Overview"), 'overview', {}),
            ],
        )
    }
    return render(request, 'tintri/templates/admin_page.html', tintri_context)

@dialog_view
def create_tintri_snapshot(request, server_id):
    profile = request.get_user_profile()
    server = get_object_or_404(Server, pk=server_id)

    if request.method == 'POST':
        form = TintriSnapshotForm(request.POST, server=server)
        action = Tintri().get_or_create_take_snapshot_server_action()
        if form.is_valid():
            context = form.save()
            action_response = action.run_hook_as_job(
                owner=profile, servers=[server], context=context
            )
            action_kwargs = {
                "action": action,
                "server": server,
                "profile": profile,
                "request": request,
            }
            _format_action_html_response(
                action_response=action_response, **action_kwargs
            )

            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = TintriSnapshotForm(server=server)

    return {
        'title': "Create Tintri Snapshot",
        'form': form,
        'use_ajax': True,
        'action_url': reverse('create_tintri_snapshot', args=[server_id]),
        'submit': 'Take Snapshot',
    }

@dialog_view
def delete_tintri_snapshot(request, server_id, snapshot_uuid):
    profile = request.get_user_profile()
    server = get_object_or_404(Server, pk=server_id)

    if request.method == 'POST':
        action = Tintri().get_or_create_delete_snapshot_server_action()
        context = {'snapshot_uuid': snapshot_uuid}
        action_response = action.run_hook_as_job(
            owner=profile, servers=[server], context=context
        )
        action_kwargs = {
            "action": action,
            "server": server,
            "profile": profile,
            "request": request,
        }
        _format_action_html_response(
            action_response=action_response, **action_kwargs
        )

        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    return {
        'title': "Delete Tintri Snapshot",
        "theme": "danger",
        "content": (
            f"Are you sure you want to delete snapshot with uuid '{snapshot_uuid}' from Tintri?"
            " This action cannot be undone!"
        ),
        'use_ajax': True,
        'action_url': reverse('delete_tintri_snapshot', args=[server_id, snapshot_uuid]),
        'submit': 'Delete',
    }

@dialog_view
def clone_from_tintri_snapshot(request, server_id, snapshot_uuid):
    profile = request.get_user_profile()
    server = get_object_or_404(Server, pk=server_id)

    if request.method == 'POST':
        form = TintriCloneSnapshotForm(request.POST, server=server)
        action = Tintri().get_or_create_clone_from_snapshot_server_action()
        if form.is_valid():
            context = form.save()
            context["snapshot_uuid"] = snapshot_uuid
            action_response = action.run_hook_as_job(
                owner=profile, servers=[server], context=context
            )
            action_kwargs = {
                "action": action,
                "server": server,
                "profile": profile,
                "request": request,
            }
            _format_action_html_response(
                action_response=action_response, **action_kwargs
            )

            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = TintriCloneSnapshotForm(server=server)

    return {
        'title': "Clone VM from Tintri Snapshot",
        'content': f"Cloning from snapshot with UUID {snapshot_uuid}",
        'form': form,
        'use_ajax': True,
        'action_url': reverse('clone_from_tintri_snapshot', args=[server_id, snapshot_uuid]),
        'submit': 'Clone From Snapshot',
    }