#!/usr/local/bin/python
import sys
import json

import requests

from infrastructure.models import Server
from jobs.models import Job
from utilities.logger import get_thread_logger
from utilities.models import ConnectionInfo


def run(job, logger=None):
    if not logger:
        logger = get_thread_logger(__name__)

    if job.status == 'FAILURE':
        return "", "", ""

    conn = ConnectionInfo.objects.get(name='servicenow')
    assert isinstance(conn, ConnectionInfo)

    servicenow_url = "{}://{}:{}".format(conn.protocol, conn.ip, conn.port)

    server = job.server_set.last()  # prov job only has one server in set
    assert isinstance(server, Server)

    job.set_progress(
        'Creating new CI in ServiceNow for server {}'.format(server.hostname))
    url = servicenow_url + "/api/now/table/{}".format("cmdb_ci_server")

    # column names for tables found at System Definition -> Tables
    table_columns = {
        'name': server.hostname,
        'company': server.group.name,
        'serial_number': server.resource_handler_svr_id,
        'asset_tag': server.resource_handler_svr_id,
        'operating_system': server.os_build.name,
        'os_version': server.os_build.name,
        'disk_space': server.disk_size,
        'cpu_core_count': server.cpu_cnt,
        'u_host_type': 'Virtual Host',
        'u_environment': 'No Environment',
        'ip_address': server.ip,
        'manufacturer': 'VMware',
        # 'ram': server.mem_size * 1024,
        'short_description': 'Created from CloudBolt job ID {}'.format(job.id),
    }

    json_data = json.dumps(table_columns)

    # create the CI
    response = request_new_ci(json_data, conn, url, logger=logger)
    if response.status_code != 201:
        err = (
            'Failed to create ServiceNow CI, response from '
            'ServiceNow:\n{}'.format(response.content)
        )
        return "FAILURE", "", err

    return "", "", ""


def request_new_ci(data, conn, url, logger=None):
    """
    Make REST call and return the response
    """
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    response = requests.post(
        url=url,
        data=data,
        auth=(conn.username, conn.password),
        headers=headers
    )
    logger.info('Response from ServiceNow:\n{}'.format(response.content))
    return response


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print '  Usage:  {} <job_id>'.format(sys.argv[0])
        sys.exit(1)

    job = Job.objects.get(id=sys.argv[1])
    print run(job)
