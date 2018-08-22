"""
Module contains all views for this extension package.
"""
import json

from django.shortcuts import render

from extensions.views import tab_extension, TabExtensionDelegate
from infrastructure.models import Server

from . import os_info_helpers


os_info_helpers.create_os_info_parameters_if_needed()


#
# All of these delegates only display their tab if the server object has the relevant OS info.
#


class OSServicesInfoTabDelegate(TabExtensionDelegate):
    def should_display(self):
        # Handle when attr is not defined and when it's empty
        val = getattr(self.instance, 'os_services', None) or None
        return val is not None


class OSUsersInfoTabDelegate(TabExtensionDelegate):
    def should_display(self):
        # Handle when attr is not defined and when it's empty
        val = getattr(self.instance, 'os_users', None) or None
        return val is not None


class OSCronInfoTabDelegate(TabExtensionDelegate):
    def should_display(self):
        # Handle when attr is not defined and when it's empty
        val = getattr(self.instance, 'os_cron', None) or None
        return val is not None


class OSDiskInfoTabDelegate(TabExtensionDelegate):
    def should_display(self):
        # Handle when attr is not defined and when it's empty
        d1 = getattr(self.instance, 'os_disks_physical', None) or None
        d2 = getattr(self.instance, 'os_partitions', None) or None
        d3 = getattr(self.instance, 'os_disks_logical', None) or None
        return (
            d1 is not None or d2 is not None or d3 is not None
        )


@tab_extension(model=Server, title='OS Services', delegate=OSServicesInfoTabDelegate)
def os_services_server_tab(request, obj_id):
    """
    This extension adds an "OS Services" tab to Servers so that you can view
    a list of services installed an a server, e.g. httpd or SQL Server.
    """
    server = Server.objects.get(id=obj_id)
    rows = []
    for row in json.loads(server.os_services):
        rows.append((
            row.get('Name'),
            row.get('DisplayName'),  # Alternative: "Caption"
            row.get('State'),
            row.get('StartMode'),
            row.get('StartName'),
            row.get('PathName')
        ))

    return render(request, 'os_info/templates/table.html', dict(
        pagetitle='OS Services',
        intro="""
        """,
        table_caption='Shows services for {}'.format(
            server.hostname if hasattr(server, 'hostname') else 'server'),
        column_headings=[
            'Service Name',
            'Service Label',
            'Status',
            'Startup',
            'Account',
            'Path'
        ],
        rows=rows,
        sort_by_column=1,
        unsortable_column_indices=[],
    ))


@tab_extension(model=Server, title='OS Users', delegate=OSUsersInfoTabDelegate)
def os_users_server_tab(request, obj_id):
    server = Server.objects.get(id=obj_id)
    rows = []
    for row in json.loads(server.os_users):
        rows.append((
            row.get('Name'),
            row.get('FullName'),
            row.get('Disabled'),
            row.get('PasswordChangeable'),
            row.get('PasswordExpires'),
            row.get('PasswordRequired')
        ))

    return render(request, 'os_info/templates/table.html', dict(
        pagetitle='OS Users',
        intro="""
        """,
        column_headings=[
            'Name',
            'Full Name',
            'Disabled',
            'Password Changeable',
            'Password Expires',
            'Password Required'
        ],
        rows=rows,
        sort_by_column=1,
        unsortable_column_indices=[],
    ))


@tab_extension(model=Server, title='OS Disks', delegate=OSDiskInfoTabDelegate)
def os_disks_server_tab(request, obj_id):
    server = Server.objects.get(id=obj_id)
    tables = []

    if server.os_disks_physical:
        tables.append(
            os_info_helpers.render_table(
                'Physical Disks',
                server.os_disks_physical,
                [
                    'InterfaceType',
                    'DeviceID',
                    'Manufacturer',
                    'Model',
                    'Partitions',
                    'Size'
                ],
                lookup_functions={
                    'Size': os_info_helpers.sizeof_fmt
                }
            )
        )
    if server.os_partitions:
        tables.append(
            os_info_helpers.render_table(
                'Disk Partitions',
                server.os_partitions,
                [
                    'DiskIndex',
                    'DeviceID',
                    'Description',
                    'PrimaryPartition',
                    'Bootable',
                    'BootPartition',
                    'NumberOfBlocks',
                    'BlockSize',
                    'Size',
                    'StartingOffset'
                ],
                lookup_functions={
                    'Size': os_info_helpers.sizeof_fmt,
                    'StartingOffset': os_info_helpers.sizeof_fmt
                }
            )
        )
    if server.os_disks_logical:
        tables.append(
            os_info_helpers.render_table(
                'Logical Disks',
                server.os_disks_logical,
                [
                    'VolumeName',
                    'DeviceID',
                    'DriveType',
                    'FileSystem',
                    'FreeSpace',
                    'MediaType',
                    'Size'
                ],
                lookup_functions={
                    'Size': os_info_helpers.sizeof_fmt,
                    'FreeSpace': os_info_helpers.sizeof_fmt,
                    'DriveType': os_info_helpers.get_drive_type,
                    'MediaType': os_info_helpers.get_media_type
                }
            )
        )

    return render(request, 'os_info/templates/tables.html', dict(
        pagetitle='OS Disks',
        intro="""
        """,
        tables=tables,
    ))


@tab_extension(model=Server, title='OS Cron', delegate=OSCronInfoTabDelegate)
def os_cron_server_tab(request, obj_id):
    server = Server.objects.get(id=obj_id)

    tables = [
        os_info_helpers.render_table(
            'Cron Jobs/Scheduled Tasks',
            server.os_cron,
            [
                'Caption',
                'Description',
                'Name',
                'Status',
                'Owner',
                'Command'
                'DaysOfMonth',
                'DaysOfWeek',
                'InteractWithDesktop',
                'JobStatus',
                'StartTime',
                'RunRepeatedly',
                'InstallDate',
                'Status'
            ]
        )
    ]

    return render(request, 'os_info/templates/tables.html', dict(
        pagetitle='OS Cron',
        intro="""
        """,
        tables=tables,
    ))
