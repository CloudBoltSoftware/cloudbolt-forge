import ast
import requests
from utilities.models import ConnectionInfo


class OpenshiftManager:
    def __init__(self, host=None, token=None, port=443, protocol='https'):
        """API Object Constructor."""
        self.BASE_URL = '{}://{}:{}/oapi/v1'.format(protocol, host, port)
        self.host = host
        self.token = token
        self.headers = {
            'Authorization': 'Bearer {}'.format(token),
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        self.verify = False
        self.port = port
        self.protocol = protocol

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
