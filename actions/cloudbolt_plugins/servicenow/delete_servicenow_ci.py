import sys

from django.utils.http import urlencode
import requests

from jobs.models import Job
from utilities.logger import get_thread_logger
from utilities.models import ConnectionInfo


def run(job, logger=None):
    if not logger:
        logger = get_thread_logger(__name__)

    # if job.status == 'FAILURE': return "", "", ""

    conn = ConnectionInfo.objects.get(name='servicenow')
    base_url = "{}://{}:{}".format(conn.protocol, conn.ip, conn.port)

    for server in job.server_set.all():
        job.set_progress('Removing CI {} from ServiceNow'.format(server.hostname))

        sysid = lookup_ci_sysid(server.resource_handler_svr_id, base_url, conn, logger)
        if not sysid:
            job.set_progress("Unable to locate {} in ServiceNow".format(server.hostname))
            return "", "", ""

        response = delete_ci(sysid, base_url, conn, logger)
        if 200 < response.status_code >= 300:
            err = (
                'Failed to create ServiceNow CI, response from '
                'ServiceNow:\n{}'.format(response.content)
            )
            job.set_progress("Unable to remove {} from ServiceNow".format(server.hostname))
            logger.error(err)

    return "", "", ""


def lookup_ci_sysid(asset_id, base_url, conn, logger=None):
    sysid = None
    query = urlencode({"sysparm_query": "asset_tag={}".format(asset_id)})
    url = base_url + "/api/now/table/cmdb_ci_server?{}".format(query)

    response = requests.get(
        url=url,
        auth=(conn.username, conn.password),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=5.0
    )

    try:
        sysid = response.json()["result"][0]["sys_id"]
    except Exception:
        pass

    return sysid


def delete_ci(sysid, base_url, conn, logger=None):
    url = base_url + "/api/now/table/cmdb_ci_server/{}".format(sysid)

    response = requests.delete(
        url=url,
        auth=(conn.username, conn.password),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=5.0
    )

    logger.info('Response from ServiceNow:\n{}'.format(response.content))
    return response


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('  Usage:  {} <job_id>'.format(sys.argv[0]))
        sys.exit(1)

    job = Job.objects.get(id=sys.argv[1])
    print(run(job))
