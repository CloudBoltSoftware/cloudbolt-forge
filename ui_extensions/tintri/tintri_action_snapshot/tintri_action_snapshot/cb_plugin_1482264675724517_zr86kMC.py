"""
This plugin is required as part of the Tintri UI Extension. It provides one of
the actions exposed on a Tintri server tab.

This Server Action should be Disabled so that it isn't shown as a button on server
detail pages. Instead, it's rendered directly by the Tintri UI extension.

Prompts user for one runtime input: snapshot name.

More about Tintri snapshots:
https://www.tintri.com/blog/2012/04/accelerating-virtualization-advanced-vm-snapshots-and-clones
"""
from xui.tintri import views as t


def run(job, logger=None, **kwargs):
    server = job.server_set.first()
    tintri = t.get_session(server)
    vm = t.get_vm(tintri, server.hostname)
    # Snapshot retention default is 4 hours
    t.vm_snapshot(tintri,
                  vm.uuid.uuid,
                  '{{ tintri_snapshot_name }}',
                  'CRASH_CONSISTENT')
    return "", "", ""
