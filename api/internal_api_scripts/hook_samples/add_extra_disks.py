"""
Sample hook for adding multiple disks to a server.

To use, create a preconfiguration value that includes the OSBuild and the disk
breakdown wanted.
"""


def run(job, logger=None):
    server = job.server_set.all()[0]
    extra_disks = server.custom_field_values.filter(field__name__contains='extra_disk')
    rh = server.resource_handler.cast()
    for disk in extra_disks:
        job.set_progress("Adding new disk to server: {}".format(disk.display_value))
        rh.init()
        rh.resource_technology.work_class.add_disk_to_server(
            server.get_vm_name(), 'THIN', disk.value
        )
    return "", "", ""
