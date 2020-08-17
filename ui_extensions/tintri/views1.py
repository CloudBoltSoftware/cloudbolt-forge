"""
Provides features to support a Tintri storage array.

Servers in environments that have a Tintri store will have a "Tintri" tab on
their detail view. This tab exposes storage performance metrics as well as some
actions users can take on the server, such as taking a snapshot.

You must create a ConnectionInfo for every CB environment whose servers want
this Tintri tab. The ConnectionInfo name should follow the pattern "Tintri
VMstore for Environment 2", where 2 is the ID of the environment. You can
determine an environment's ID by inspecting the URL for its detail page.
"""
import os
import datetime
import json
import time
import logging

from django.shortcuts import get_object_or_404, render
from extensions.views import tab_extension, TabExtensionDelegate
from utilities.models import ConnectionInfo
from infrastructure.models import Server
from cbhooks.models import ServerAction
try:
    from tintri.common import TintriServerError
    from tintri.v310 import Tintri, VirtualMachineStat
    from tintri.v310 import VirtualMachineFilterSpec
    from tintri.v310 import SnapshotSpec
    from tintri.v310 import VirtualMachineCloneSpec
    from tintri.v310 import VMwareCloneInfo
except:
    # log the fact that this appliance is missing the tintir cli
    pass
from dateutil import parser
from .tintri import Tintri

"""
UI Extension view using Tintri PySDK
https://github.com/Tintri/tintri-python-sdk
"""

COLOR1 = '#2A17B1'
COLOR2 = '#FF9E00'
COLOR3 = '#00A67C'


def get_ci(server):
    ci = ConnectionInfo.objects.filter(name='Tintri').first()
    if not ci:
        return None
    t = {}
    t['ip'] = ci.ip
    t['username'] = ci.username
    t['password'] = ci.password
    return t


def get_session(server):
    '''
    Get authenticated Tintri Session for the given server

    Requires:
        ConnectionInfo object with name 'Tintri VMstore for Environment X'
        Otherwise return None

    Args:
        server (obj): CB server object

    Returns:
        tintri: Tintri object
    '''
    conn = get_ci(server)
    if not conn:
        return None
    # instantiate the Tintri server.
    tintri = Tintri(conn['ip'])
    # Login to VMstore
    tintri.login(conn['username'], conn['password'])
    return tintri


def get_appliance_info(tintri):
    '''
    Get Tintri Appliance details

    Args:
        tintri (obj): Tintri object

    Returns:
        appliance: Dict of apliance details
    '''
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


def get_vm(tintri, vm_name):
    '''
    Get Tintri Virtual Machine object by VM name

    Args:
        tintri  (obj): Tintri object with session_id
        vm_name (str): Virtual Machine's name

    Returns:
        vm: Tintri Virtual Machine
    '''
    logging.info('Requesting VM details from Tintri for VM: "{}"'.format(vm_name))
    results = tintri.get_vms(name='ESXi-6.0')
    if results.json().get('filteredTotal') == 0:
        msg = 'No VMs found for get VM request with NAME: "{}"'.format(vm_name)
        raise Exception(msg)
    else:
        vm = {}
        items = results.json().get('items')[0]
        vm['name']= items.get("vmware").get("name")
        vm['uuid'] = items.get("uuid").get("uuid")

        logging.info(f'Found Tintri VM with Name: "{vm.get("name")}"'
                     f' and UUID: {vm.get("uuid")}')

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
    # Specify date range for stats
    # The end date in ISO8601 format - 'YYYY-MM-DDThh:mm:ss.ms-/+zz:zz'
    until = datetime.datetime.now()
    since = until - datetime.timedelta(days=days)
    until = until.isoformat()[:-3] + '-00:00'
    since = since.isoformat()[:-3] + '-00:00'

    results = tintri.get_vm_historic_stats(uuid=vm_uuid,since=since, until=until)

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


def get_tintri_actions():
    """
    Get all of the tintri server action ID's in a {}

    Args: None

    Returns:
        tintri_actions: {} of action ID's
    """
    tintri_actions = []
    snapshot_action = ServerAction.objects.get(label='Take a Tintri Snapshot')
    if snapshot_action:
        tintri_actions.append(snapshot_action)
    clone_action = ServerAction.objects.get(label='Clone VM using Tintri')
    if clone_action:
        tintri_actions.append(clone_action)
    return tintri_actions

def vm_snapshot(tintri, vm_uuid, snapshot_name, consistency_type):
    '''
    Tintri snapshot of Virtual Machine

    Args:
        tintri           (obj): Tintri object with session_id
        vm_uuid          (str): Virtual Machine's UUID
        snapshot_name    (str): Name of the snapshot
        consistency_type (str): 'CRASH_CONSISTENT' 'VM_CONSISTENT'

    Returns:
        snapshot_name: Name of snapshot
    '''
    snapshot_spec = SnapshotSpec()
    snapshot_spec.consistency = consistency_type
    snapshot_spec.retentionMinutes = 240  # 4 hours
    snapshot_spec.snapshotName = snapshot_name
    snapshot_spec.sourceVmTintriUUID = vm_uuid

    snapshot_specs = [snapshot_spec]
    result = tintri.create_snapshot(snapshot_specs)
    if result[0]:
        snapshot_name = result[0]
        return snapshot_name


def vm_clone(tintri, tintri_vm, clone_name, qty=1, dstore_name='default'):
    '''
    Tintri clone of Virtual Machine

    Issue: Cloning completes but duplicated VMWare VM UUID

    Args:
        tintri      (obj): Tintri object with session_id
        tintri_vm   (obj): VM object from get_vm()
        clone_name  (str): Name for vm clone
        qty         (int): How many clones
        dstore_name (str): 'default' for VMStore

    Returns:
        clone_state: 'COMPLETED' 'FAILED'
    '''
    clone_spec = VirtualMachineCloneSpec()
    clone_spec.vmId = tintri_vm.uuid.uuid
    clone_spec.consistency = 'CRASH_CONSISTENT'
    clone_spec.count = qty

    vmware_clone_info = VMwareCloneInfo()
    clone_spec.vmware = vmware_clone_info
    clone_spec.vmware.cloneVmName = clone_name
    clone_spec.vmware.vCenterName = tintri_vm.vmware.vcenterName
    clone_spec.vmware.datastoreName = dstore_name

    # Run as CloudBolt Job
    task = tintri.clone_vm(clone_spec, True)

    # task_uuid = task.uuid.uuid
    # task_state = task.state
    # task_progress = task.progressDescription
    # task_type = task.type
    return task


def vm_protect(tintri, tintri_vm):
    '''
    Note: Not yet implemented

    Tintri protect Virtual Machine

    Args:
        tintri    (obj): Tintri object with session_id
        tintri_vm (obj): VM object from get_vm()

    Returns:
    '''
    pass


def vm_restore(tinri, tintri_vm):
    '''
    Note: Not yet implemented

    Tintri restore Virtual Machine

    Args:
        tintri    (obj): Tintri object with session_id
        tintri_vm (obj): VM object from get_vm()

    Returns:
    '''
    pass


class TintriTabDelegate(TabExtensionDelegate):
    def should_display(self):
        #if get_ci(server=self.instance):
        return True
        #return False


def dict_to_vmstat(statdict):
    vmstat = VirtualMachineStat()
    for k, v in statdict.items():
        setattr(vmstat, k, v)
    return vmstat


@tab_extension(model=Server,
               title='Tintri',
               description='Tintri Server Tab',
               delegate=TintriTabDelegate)
def server_tab_tintri(request, obj_id=None):
    """
    Tintri Server Tab Extension
    Requires:
        Install Tintri PySDK
        ConnectionInfo object with name 'tintri'
        VCenter cluster with Tintri VMStore
    """
    server = get_object_or_404(Server, pk=obj_id)

    mydir = os.path.dirname(os.path.realpath(__file__))

    if server.tags.filter(name='demdo'):
        with open(os.path.join(mydir, 'demo.json')) as data_file:
            # When using the demo JSON, to get the graphs to appear, the 'time' and 'endTime'
            # values need to be updated to be within the last day. TODO: automate this here
            vm_stat_dicts = json.load(data_file)
            vm_stats = []
            for statdict in vm_stat_dicts:
                vm_stats.append(dict_to_vmstat(statdict))

        maxNormalizedIops = 1000
        appliance_info = {
            'product': 'Tintri VMstore',
            'model': 'T5000'
        }
    else:
        # get real stats from Tintri
        vm_name = server.hostname
        tintri = get_session(server)
        appliance_info = get_appliance_info(tintri)
        vm = get_vm(tintri, vm_name)
        vm_stats = get_vm_stats(tintri, vm.get('uuid'), days=1)
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
    tintri_data = {
        "disk_used": format(sorted_stats.get('spaceUsedGiB'),
                            '.1f'),
        "disk_provisioned": format(sorted_stats.get('spaceProvisionedGiB'),
                                   '.1f'),
        "disk_changed": format(sorted_stats.get('spaceUsedChangeGiB'),
                               '.1f'),
        "chart_latency": latency,
        "chart_iops": iops,
        "chart_throughput": throughput,
        "max_line_color": "red",
    }

    return render(
        request, 'tintri/templates/server_tab.html', dict(
            appliance_info=appliance_info,
            tintri_data=tintri_data,
            tintri_actions=get_tintri_actions(),
            server=server,
            connection_info=get_ci(server),
        )
    )
