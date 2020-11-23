import requests
import json
from common.methods import generate_string_from_template
from utilities.models import ConnectionInfo
from api.api_samples.python_client.api_client import CloudBoltAPIClient

class ContentMetaData:
    def __init__(self):
        ci = ConnectionInfo.objects.filter(
            name__iexact='CB API Client').first()
        self.connection_info = ci
        self.endpoint = 'api/v2/{}'
        
    def get_connection_info(self):
        return self.connection_info
    
    def get_api_client(self):
        ci = self.connection_info
        return CloudBoltAPIClient(
        ci.username, ci.password, ci.ip, ci.port, protocol=ci.protocol)
        
    def get_exportable_content(self):
        client = self.get_api_client()
        endpoint = self.endpoint.format('exportable-content/')
        res = client.get(endpoint)
        response = json.loads(res)
        return [n['name'] for n in response.get('actions')]
