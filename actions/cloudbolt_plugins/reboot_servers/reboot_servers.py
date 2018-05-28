"""
This plug-in can be used in various contexts to reboot the server(s) available
to it, or some subset thereof. For example, you can reboot a single server after
it is provisioned by adding this at the Post-Network Configuration trigger point
for orchestration actions.
"""
import time
from common.methods import set_progress

SERVER_TIER = str('{{ SERVER_TIER }}')


def run(job, logger=None, **kwargs):
    bpc = kwargs.get('blueprint_context')
    if bpc and SERVER_TIER:
        servers = bpc[SERVER_TIER]['servers']
    else:
        servers = job.server_set.all()

    # In some cases, such as a provision job, this will only contain 1 server.
    # To only reboot a subset of the servers, you can filter this group. For
    # example, to only reboot those whose hostname starts with CB you can do:
    # servers = [svr for svr in servers if svr.hostname.startswith('CB')]
    profile = None
    if job:
        profile = job.owner

    failed_servers = []
    for server in servers:
        if server.can_reboot():
            set_progress("Rebooting server '{}'".format(server.hostname))
            success = server.reboot(profile)
            if not success:
                failed_servers.append(server.hostname)
            # Wait 20s for the reboot to begin so the call to
            # wait_for_os_readiness does not return immediately because the
            # server hasn't started rebooting yet
            time.sleep(20)
            server.wait_for_os_readiness()
        else:
            set_progress("Skipping reboot of server '{}' because not supported"
                         .format(server.hostname))

    if failed_servers:
        failed_list = ', '.join(failed_servers)
        return 'WARNING', 'Rebooting failed on {}'.format(failed_list), ''

    return 'SUCCESS', '', ''
