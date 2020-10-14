import requests
import json
import ast
from datetime import datetime

from utilities.models import ConnectionInfo
from common.methods import set_progress
from infrastructure.models import CustomField


def create_custom_fields_as_needed():
    CustomField.objects.get_or_create(
        name='openshift_project_name',
        label='OpenShift Project Name',
        defaults={'type': 'STR',
                  'show_as_attribute': True
                  }
    )
    CustomField.objects.get_or_create(
        name='openshift_project_description',
        label='OpenShift Project description',
        defaults={'type': 'STR',
                  'show_as_attribute': True
                  }
    )


def run(resource, **kwargs):
    create_custom_fields_as_needed()
    projectname = '{{ project_name }}'
    display_name = '{{ display_name }}'
    description = '{{ description }}'

    # Create Project in Openshift Cluster
    set_progress('Creating Project in OpenShift Cluster...')
    openshift = OpenshiftAPI()
    openshift_ci = openshift.get_connection_info()
    if not openshift_ci:
        return "FAILURE", "Openshift not configured. Use the Openshift Admin page to do the configuration.", ""

    oc_api = OpenshiftAPI(host=openshift_ci.ip, token=openshift.get_token(), port=openshift_ci.port)
    try:
        oc_api.create_project(projectname, display_name, description)

        # Create Resource in Cloudbolt
        resource.name = display_name
        resource.openshift_project_name = projectname
        resource.openshift_project_description = description
        resource.save()

        return 'SUCCESS', f'{projectname} Successfully created', ''
    except Exception as e:
        return 'FAILURE', f'{e}', f'Failed to create project {projectname}'


class OpenshiftAPI(object):
    """Object for API calls to OpenShift Cluster."""

    def __init__(self, host=None, token=None, port=443, protocol='https'):
        """API Object Constructor."""
        self.BASE_URL = f'{protocol}://{host}:{port}/apis/project.openshift.io/v1'
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

    def create_project(self, project_name, display_name, description=''):
        """Creates the Project with specified project_name in Openshift Cluster."""
        url = f'{self.BASE_URL}/projectrequests'
        data = {
            "kind": "ProjectRequest",
            "apiVersion": "project.openshift.io/v1",
            "metadata": {
                "name": project_name, },
            "displayName": display_name,
            "description": description
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
        return r

    def beautify_time(self, time_str):
        time = time_str[:-1].replace('T', " ")
        return datetime.strptime(time, '%Y-%m-%d %H:%M:%S')

    def verify_rest_credentials(self):
        try:
            return requests.get(self.BASE_URL, headers=self.headers, verify=self.verify, timeout=5).ok
        except Exception:
            return False

    def get_connection_info(self):
        return ConnectionInfo.objects.filter(name__iexact='Openshift Connection Info').first()

    def get_token(self):
        connection_info = self.get_connection_info()
        if connection_info:
            headers = ast.literal_eval(connection_info.headers)
            return headers.get('token')
        return None
