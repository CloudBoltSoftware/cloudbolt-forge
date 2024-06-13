"""
Script looks at all servers with status ACTIVE to identify any that have a UUID
matching another server's UUID (an unexpected condition in CloudBolt). Prints
some information about each of the "duplicate" servers to stdout.

Usage:
./manage runscript find_dup_server_uuids
or
./manage runscript find_dup_server_uuids > dup_servers.txt
"""
from copy import copy

from infrastructure.models import Server


def server_info(s):
    rh = s.environment.resource_handler
    return """
    id: {id}
    mac: {mac}
    ip: {ip}
    hostname: {hostname}
    owner: {owner}
    env: {env}
    rh: {rh}
    """.format(
        id=s.id,
        mac=s.mac,
        ip=s.ip,
        hostname=s.hostname,
        owner=s.owner,
        env=s.environment,
        rh=rh,
    )


def run(*args):
    print 'Looking for multiple servers with same UUID...'

    servers = list(Server.objects.filter(status__in=['ACTIVE']))
    servers2 = copy(servers)
    found = []

    for s1 in servers:
        for s2 in servers2:
            if s2.id == s1.id or s2.resource_handler_svr_id in found:
                continue

            if (s2.resource_handler_svr_id and
                    s2.resource_handler_svr_id == s1.resource_handler_svr_id):
                found.append(s2.resource_handler_svr_id)
                print '2nd server found for UUID {}'.format(s2.resource_handler_svr_id)
                print '  server 1: {}'.format(server_info(s1))
                print '  server 2: {}'.format(server_info(s2))



    print "\nFound {} total UUIDs with more than one C2 server record.".format(len(found))
    print "\n".join([uuid for uuid in found])
    if "delete-all-duplicates" in args:
        print "\nNext deleting all server records those UUIDs"
        Server.objects.filter(resource_handler_svr_id__in=found).delete()
        print "\nDone deleting, next sync VMs"
