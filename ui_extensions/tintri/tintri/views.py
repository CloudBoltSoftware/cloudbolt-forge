from django.shortcuts import get_object_or_404, render
from extensions.views import tab_extension, TabExtensionDelegate
from utilities.models import ConnectionInfo
from infrastructure.models import Server
from cbhooks.models import ServerAction
from tintri.common import TintriServerError
from tintri.v310 import Tintri
from tintri.v310 import VirtualMachineFilterSpec
from tintri.v310 import PageFilterSpec
from tintri.v310 import SnapshotSpec
from tintri.v310 import VirtualMachineCloneSpec
from tintri.v310 import VMwareCloneInfo
from dateutil import parser
import datetime
import time
import logging
"""
UI Extension view using Tintri PySDK
https://github.com/Tintri/tintri-python-sdk
"""


def get_ci():
    ci = ConnectionInfo.objects.get(name='tintri')
    t = {}
    t['ip'] = ci.ip
    t['username'] = ci.username
    t['password'] = ci.password
    return t


def get_session():
    '''
    Get authenticated Tintri Session

    Requires:
        ConnectionInfo object with name 'tintri'

    Args:
        host (str): Tintri VMSTore IP/Hostname
        uid  (str): Tintri username
        pwd  (str): Tintri password

    Returns:
        tintri: Tintri object
    '''
    # ci = ConnectionInfo.objects.get(name='tintri')
    conn = get_ci()
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
        host   (str): Tintri VMSTore IP/Hostname

    Returns:
        appliance: Dict of apliance details
    '''
    appliance = {}
    info = tintri.get_appliance_info('default')
    if tintri.is_vmstore():
        product = 'Tintri VMstore'
    elif tintri.is_tgc():
        product = 'Tintri Global Center'
    appliance['product'] = product
    appliance['model'] = info.modelName
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
    vm_filter_spec = VirtualMachineFilterSpec()
    vm_filter_spec.name = vm_name
    logging.info('Requesting VM details from Tintri for VM: "{}"'.format(vm_name))
    results = tintri.get_vms(filters=vm_filter_spec)
    if results.filteredTotal == 0:
        msg = 'No VMs found for get VM request with NAME: "{}"'.format(vm_name)
        raise TintriServerError(0, cause=msg)
    else:
        vm = results.next()
        logging.info('Found Tintri VM with Name: "{}" and UUID: "{}"'.format(vm.vmware.name,
                                                                             vm.uuid.uuid))
        return vm


def get_vm_stats(tintri, vm_uuid, days):
    '''
    Get all Tintri Virtual Machine stats for X days

    Args:
        tintri  (obj): Tintri object with session_id
        vm_uuid (str): Virtual Machine's UUID
        days    (int): Total days of stats

    Returns:
        sorted_stats: [] of sorted stats
    '''
    vm_stats_filter_spec = VirtualMachineFilterSpec()
    # Specify date range for stats
    # The end date in ISO8601 format - 'YYYY-MM-DDThh:mm:ss.ms-/+zz:zz'
    until = datetime.datetime.now()
    since = until - datetime.timedelta(days=days)
    vm_stats_filter_spec.until = until.isoformat()[:-3] + '+00:00'
    vm_stats_filter_spec.since = since.isoformat()[:-3] + '+00:00'
    vm_stats_filter_spec.uuid = vm_uuid
    results = tintri.get_vm_historic_stats(vm_uuid,
                                           filters=vm_stats_filter_spec)
    if results.filteredTotal == 0:
        raise TintriServerError(0, cause="No VMs found for vm stats request")
    else:
        stats = results.next()
        sorted_stats = stats.sortedStats
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
        a = getattr(stat, attr)
        date = parser.parse(stat.timeEnd)
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
    '''
    Get all of the tintri server action ID's in a {}

    Args: None

    Returns:
        tintri_actions: {} of action ID's
    '''
    snapshot_id = ServerAction.objects.get(label='tintri_action_snapshot').id
    clone_id = ServerAction.objects.get(label='tintri_action_clone').id
    tintri_actions = {}
    tintri_actions['snapshot'] = snapshot_id
    tintri_actions['clone'] = clone_id
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
        if hasattr(self, 'instance'):
            if self.instance.tags.filter(name='tintri'):
                return True
        elif hasattr(self, 'model'):
            if self.model.tags.filter(name='tintri'):
                return True
        return False


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
    vm_name = server.hostname
    tintri = get_session()
    appliance_info = get_appliance_info(tintri)
    vm = get_vm(tintri, vm_name)
    vm_uuid = vm.uuid.uuid
    qos_config = vm.qosConfig
    vm_stats = get_vm_stats(tintri, vm_uuid, days=1)
    sorted_stats = vm_stats[-1]
    latency = [
        get_chart_plotline(vm_stats,
                           attr='latencyNetworkMs',
                           name='Network',
                           color='#DFC245'),
        get_chart_plotline(vm_stats,
                           attr='latencyHostMs',
                           name='Host',
                           color='#468875'),
        get_chart_plotline(vm_stats,
                           attr='latencyDiskMs',
                           name='Storage',
                           color='#5A7FAB'),
    ]
    iops = [
        get_chart_plotline(vm_stats,
                           attr='normalizedTotalIops',
                           name='Total',
                           color='#DFC245'),
    ]
    throughput = [
        get_chart_plotline(vm_stats,
                           attr='throughputReadMBps',
                           name='Read',
                           color='#5A7FAB'),
        get_chart_plotline(vm_stats,
                           attr='throughputWriteMBps',
                           name='Write',
                           color='#468875'),
    ]
    tintri_data = {
        "disk_used": format(sorted_stats.spaceUsedGiB,
                            '.1f'),
        "disk_provisioned": format(sorted_stats.spaceProvisionedGiB,
                                   '.1f'),
        "disk_changed": format(sorted_stats.spaceUsedChangeGiB,
                               '.1f'),
        "chart_latency": latency,
        "chart_iops": iops,
        "chart_throughput": throughput,
        "max_iops": qos_config.maxNormalizedIops,
        "max_line_color": "red",
    }

    return render(request, 'tintri/templates/server_tab.html', dict(
                  appliance_info=appliance_info,
                  tintri_data=tintri_data,
                  tintri_actions=get_tintri_actions(),
                  server=server,))
