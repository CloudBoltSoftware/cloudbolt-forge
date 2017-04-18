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
