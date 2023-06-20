import requests
from utilities.models import ConnectionInfo
import ast


def run(resource, **kwargs):
    openshift = OpenshiftAPI()
    openshift_ci = openshift.get_connection_info()
    if not openshift_ci:
        return "FAILURE", "Openshift not configured. Use the Openshift Admin page to do the configuration.", ""
    oc_api = OpenshiftAPI(host=openshift_ci.ip, token=openshift.get_token(), port=openshift_ci.port)
    oc_api.delete_project(resource.openshift_project_name)
    return 'SUCCESS', '', ''


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

    def get_connection_info(self):
        return ConnectionInfo.objects.filter(name__iexact='Openshift Connection Info').first()

    def get_token(self):
        connection_info = self.get_connection_info()
        if connection_info:
            headers = ast.literal_eval(connection_info.headers)
            return headers.get('token')
        return None

    def delete_project(self, project_name):
        """Deletes the Project with specified project_name in Openshift Cluster."""
        url = f'{self.BASE_URL}/projects/{project_name}'
        r = requests.delete(url, headers=self.headers, verify=self.verify)
        if r.ok:
            return
        raise Exception("Return code: {}, response text: {}".format(r.status_code, r.text))
