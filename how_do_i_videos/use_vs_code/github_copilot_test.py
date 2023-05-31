



def run(job, server=None, *args, **kwargs):
    set_progress("Hello World!")
    get_all_snapshots_from_vm(server)
    return "SUCCESS", "Hello World!", ""


def get_all_snapshots_from_vm(server):
    """
    Taking a CloudBolt Server object get the corresponding vCenter VM from 
    pyvmomi and return all snapshots for that VM.
    """
    rh = server.resource_handler.cast()
    si = rh.get_api_wrapper().si_connection
    si_content = si.RetrieveContent()
    vm = si_content.searchIndex.FindByUuid(None, server.resource_handler_svr_id, True)
    if vm:
        return vm.snapshot.rootSnapshotList
    else:
        return None

