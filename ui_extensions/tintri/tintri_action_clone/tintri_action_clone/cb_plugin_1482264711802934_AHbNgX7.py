from xui.tintri import views as t


def run(job, logger=None, **kwargs):
    server = job.server_set.first()
    tintri = t.get_session(server)
    tintri_vm = t.get_vm(tintri, server.hostname)
    t.vm_clone(tintri,
               tintri_vm,
               '{{ tintri_clone_name }}')
    return "", "", ""
