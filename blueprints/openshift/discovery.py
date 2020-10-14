import requests
import json
import ast
from datetime import datetime

from utilities.models import ConnectionInfo
from common.methods import set_progress

RESOURCE_IDENTIFIER = 'openshift_project_name'


def discover_resources(**kwargs):
    discovered_projects = []
    openshift = OpenshiftAPI()
    openshift_ci = openshift.get_connection_info()
    if not openshift_ci:
        return "FAILURE", "Openshift not configured. Use the Openshift Admin page to do the configuration.", ""
    oc_api = OpenshiftAPI(host=openshift_ci.ip, token=openshift.get_token(), port=openshift_ci.port)
    try:
        projects = oc_api.get_projects()
        for project in projects:
            project = project.get('metadata')
            set_progress(f"Found {project.get('name')}")
            display_name = project.get('annotations').get('openshift.io/display-name')
            description = project.get('annotations').get('openshift.io/description')
            if display_name == '':
                display_name = project.get('name')
            discovered_projects.append({
                'name': display_name,
                'openshift_project_name': project.get('name'),
                'openshift_project_description': description
            })
        return discovered_projects

    except Exception as e:
        return 'FAILURE', f'{e}', f'Failed to get projects'


class OpenshiftAPI(object):
    """Object for API calls to OpenShift Cluster."""

    def __init__(self, host=None, token=None, port=443, protocol='https'):
        """API Object Constructor."""
        self.BASE_URL = f'{protocol}://{host}:{port}/oapi/v1'
        self.host = host
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        self.verify = False
        self.port = port
        self.protocol = protocol

    def create_project(self, project_name):
        """Creates the Project with specified project_name in Openshift Cluster."""
        url = f'{self.BASE_URL}/projects'
        data = {
            "kind": "Project",
            "apiVersion": "v1",
            "metadata": {
                "name": project_name
            }
        }
        r = requests.post(url, headers=self.headers, verify=self.verify, data=json.dumps(data))
        if r.status_code != 201:
            raise Exception("Return code: {}, response text: {}".format(r.status_code, r.text))
        return r

    def get_projects(self):
        """
        Gets all projects in an OpenShift cluster
        """
        url = f'{self.BASE_URL}/projects'
        r = requests.get(url, headers=self.headers, verify=self.verify)
        if r.status_code != 200:
            raise Exception("Return code: {}, response text: {}".format(r.status_code, r.text))
        projects = r.json().get('items')
        return projects

    def beautify_time(self, time_str):
        time = time_str[:-1].replace('T', " ")
        return datetime.strptime(time, '%Y-%m-%d %H:%M:%S')

    def verify_rest_credentials(self):
        try:
            return requests.get(self.BASE_URL, headers=self.headers, verify=self.verify, timeout=5).ok
        except Exception as e:
            return False

    def get_connection_info(self):
        return ConnectionInfo.objects.filter(name__iexact='Openshift Connection Info').first()

    def get_token(self):
        connection_info = self.get_connection_info()
        if connection_info:
            headers = ast.literal_eval(connection_info.headers)
            return headers.get('token')
        return None
