'''
'''
from common.methods import set_progress
from utilities.models import ConnectionInfo
from utilities.helpers import get_ssl_verification
import requests

CONN, _ = ConnectionInfo.objects.get_or_create(name='Ansible Tower')
assert isinstance(CONN, ConnectionInfo)

BASE_URL = "{}://{}:{}/api/v2".format(CONN.protocol, CONN.ip, CONN.port)
HEADERS = {'Content-Type': 'application/json'}

DISABLE_ONLY = bool('{{ disable_only }}')


def get_token():
    url = BASE_URL + '/tokens/'
    auth = (CONN.username, CONN.password)
    data = {'application': '', 'description': 'CloudBolt Access Token', 'scope': 'write'}
    response = requests.post(url, headers=HEADERS, auth=auth, json=data, verify=get_ssl_verification())
    results = response.json()
    token = results['token']
    HEADERS['Authorization'] = 'Bearer ' + token
    return response


def delete_token(token):
    url = BASE_URL + '/tokens/{}/'.format(token['id'])
    response = requests.delete(url, headers=HEADERS, verify=get_ssl_verification())
    return response


def update_ansible_host(host_id, params=None):
    url = BASE_URL + '/hosts/{}/'.format(host_id)
    response = requests.put(url, headers=HEADERS, json=params, verify=get_ssl_verification())
    return response


def delete_ansible_host(host_id):
    url = BASE_URL + '/hosts/{}/'.format(host_id)
    response = requests.delete(url, headers=HEADERS, verify=get_ssl_verification())
    return response


def get_ansible_host(name):
    url = BASE_URL + '/hosts/?name={}'.format(name)
    response = requests.get(url, headers=HEADERS, verify=get_ssl_verification()).json()
    results = response.get('results', None)
    host_id = None
    if results:
        result = results[0]
        host_id = result.get('id', None)
        if host_id:
            set_progress('Ansible Tower: Found Host ID: {}'.format(host_id))
    return host_id


def run(job=None, logger=None, server=None, resource=None, **kwargs):
    token = get_token().json()
    host_id = get_ansible_host(server.ip)
    delete_token(token)
    if host_id:
        if DISABLE_ONLY:
            params = {"name": server.ip, "enabled": False}
            update_ansible_host(host_id, params=params)
            set_progress('Ansible Tower: Disabled Host ID: {}'.format(host_id))
        else:
            delete_ansible_host(host_id)
            set_progress('Ansible Tower: Deleted Host ID: {}'.format(host_id))

    return "SUCCESS", "", ""
