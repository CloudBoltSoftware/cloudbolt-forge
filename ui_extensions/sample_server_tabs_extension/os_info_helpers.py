"""
Functions used by os_info.views
"""
import json
from infrastructure.models import CustomField
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


WIN_SVC_TYPES = {
    0x1: ('SERVICE_KERNEL_DRIVER', 'Driver'),
    0x2: ('SERVICE_FILE_SYSTEM_DRIVER', 'File System Driver'),
    0x10: ('SERVICE_WIN32_OWN_PROCESS', 'Runs in Own Process'),
    0x20: ('SERVICE_WIN32_SHARE_PROCESS', 'Shares Process'),
    0x100: ('SERVICE_INTERACTIVE_PROCESS', 'Interacts With Desktop')
}


WIN_SVC_STATES = {
    1: ('SERVICE_STOPPED', 'Stopped'),
    2: ('SERVICE_START_PENDING', 'Starting'),
    3: ('SERVICE_STOP_PENDING', 'Stopping'),
    4: ('SERVICE_RUNNING', 'Running'),
    5: ('SERVICE_CONTINUE_PENDING', 'Continue Pending'),
    6: ('SERVICE_PAUSE_PENDING', 'Pause Pending'),
    7: ('SERVICE_PAUSED', 'Paused')
}


def create_os_info_parameters_if_needed():
    """
    This UI extension is smart enough to create the CFs it needs. Six fewer steps for admins to do.
    """
    params = [
        ['os_cron', 'OS Cron', 'JSON-serialized OS-specific cron jobs installed on a computer.'],
        ['os_partitions', 'OS Partitions', 'JSON-serialized OS-specific partitions on a computer.'],
        ['os_disks_physical', 'OS Disks Physical', 'JSON-serialized OS-specific physical disks on a computer.'],
        ['os_disks_logical', 'OS Disks Logical', 'JSON-serialized OS-specific logical disks on a computer.'],
        ['os_users', 'OS Users', 'JSON-serialized OS-specific users on a computer.'],
        ['os_services', 'OS Services', 'JSON-serialized OS-specific services on a computer.'],
    ]

    for name, label, desc in params:
        cf, created = CustomField.objects.get_or_create(name=name)
        if created:
            cf.label = label
            cf.description = desc
            cf.type = 'CODE'
            cf.save()

            logger.info('Created new parameter {} for the OS Info UI extension.'
                        .format(name))


def win_state_for(state_code):
    return WIN_SVC_STATES.get(state_code, 'Unknown: {}'.format(state_code))


def get_media_type(id):
    table = {
        0: 'Unknown format',
        1: '5.25" Floppy Disk - 1.2 MB - 512 bytes/sector',
        2: '3.5" Floppy Disk - 1.44 MB - 512 bytes/sector',
        3: '3.5" Floppy Disk - 2.88 MB - 512 bytes/sector',
        4: '3.5" Floppy Disk - 20.8 MB - 512 bytes/sector',
        5: '3.5" Floppy Disk - 720 KB - 512 bytes/sector',
        6: '5.25" Floppy Disk - 360 KB - 512 bytes/sector',
        7: '5.25" Floppy Disk - 320 KB - 512 bytes/sector',
        8: '5.25" Floppy Disk - 320 KB - 1024 bytes/sector',
        9: '5.25" Floppy Disk - 180 KB - 512 bytes/sector',
        10: '5.25" Floppy Disk - 160 KB - 512 bytes/sector',
        11: 'Removable media other than floppy',
        12: 'Fixed hard disk media',
        13: '3.5" Floppy Disk - 120 MB - 512 bytes/sector',
        14: '3.5" Floppy Disk - 640 KB - 512 bytes/sector',
        15: '5.25" Floppy Disk - 640 KB - 512 bytes/sector',
        16: '5.25" Floppy Disk - 720 KB - 512 bytes/sector',
        17: '3.5" Floppy Disk - 1.2 MB - 512 bytes/sector',
        18: '3.5" Floppy Disk - 1.23 MB - 1024 bytes/sector',
        19: '5.25" Floppy Disk - 1.23 MB - 1024 bytes/sector',
        20: '3.5" Floppy Disk - 128 MB - 512 bytes/sector',
        20: '3.5" Floppy Disk - 230 MB - 512 bytes/sector',
        20: '8" Floppy Disk - 230 KB - 128 bytes/sector'
    }
    return table.get(id, id)


def get_drive_type(id):
    table = {
        0: 'Unknown',
        1: 'No Root Directory',
        2: 'Removable Disk',
        3: 'Local Disk',
        4: 'Network Drive',
        5: 'Compact Disc',
        6: 'RAM Disk'
    }
    return table.get(id, id)


def sizeof_fmt(num, suffix='B'):
    if num is None:
        return None
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def render_table(caption, data, fields, lookup_functions=None):
    rows = []
    data = json.loads(data, strict=False)
    for row in data:
        _row = []
        for field in fields:
            col = row.get(field, '')
            if lookup_functions and field in lookup_functions:
                col = lookup_functions[field](col)
            _row.append(col)
        rows.append(_row)
    return {
        'caption': caption,
        'column_headings': fields,
        'rows': rows,
        'sort_by_column': 0,
        'unsortable_column_indices': []
    }


