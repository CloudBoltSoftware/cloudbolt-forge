"""
This Shared Module Template has the common imports, methods and classes that are
used to start working with an external integration via REST API. This creates a
Wrapper class that can be used to make GET, POST, PATCH, PUT, and DELETE
requests to a REST API.

Steps to use:
1. Update the code below for your specific endpoint
2. Create a new Shared Module in your CloudBolt instance - copy the updated code
3. Create a new Connection Info object in CloudBolt for your endpoint

Consume this Shared Module in other CloudBolt Plugins by running the following:
from shared_module_template import RestConnection
with RestConnection(conn_info_id) as conn:
    # Use conn to make requests to the REST API
    response = conn.get('/some_endpoint')
    # response is a JSON object that can be used in your plugin
"""
# Common imports for Integrations below:
from common.methods import set_progress
from utilities.models import ConnectionInfo
from requests import Session
import json
import time
import base64
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

# Global default variables can be set here
VERIFY_CERTS = False


class RestConnection(Session):
    """
    Wrapper for connecting to a generic REST API.
    """

    def __init__(self, conn_info_id):
        """
        :param conn_info_id: The ID of the ConnectionInfo object to use
        """
        # Initialize the Session object
        super(RestConnection, self).__init__()
        # Connection Info could also be referenced by name if needed
        self.conn_info = ConnectionInfo.objects.get(id=conn_info_id)
        self.root_url = f'{self.conn_info.protocol}://{self.conn_info.ip}'
        if self.conn_info.port:
            self.root_url = f'{self.root_url}:{self.conn_info.port}'
        # Sample base URL for a REST endpoint - update for your integration
        self.base_url = f'{self.root_url}/api/v2'
        self.verify = VERIFY_CERTS

    def __enter__(self):
        self.set_headers()
        return self

    def __exit__(self, *args):
        self.close()

    def set_headers(self):
        """
        Get the headers for the REST API
        """
        self.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        """
        There are numerous ways to authenticate with a REST API. The two most
        common are using a long term Bearer Token that is stored in the password
        field of the ConnectionInfo object, or using a Basic Auth username and
        password. Update the code below to match the authentication method
        
        API Token Example: 
        headers['Authorization'] = f'Bearer {self.conn_info.password}'

        Basic Auth example (if creds need to be a base64 string):
        creds = f'{self.conn_info.username}:{self.conn_info.password}'
        base_64 = base64.b64encode(f'{creds}'.encode("ascii")).decode('ascii')
        headers['Authorization'] = f'Basic {base_64}'
        """
        # More commonly, basic auth is used to get a short term token used for a
        # session:
        token = self.get_token()
        self.headers.update({'Authorization': f'Bearer {token}'})
        return


    def get_token(self):
        """
        Example method for getting a token from the REST API
        """
        url = f'{self.base_url}/token'
        data = {
            'username': self.conn_info.username,
            'password': self.conn_info.password
        }
        response = self.post(url, data)
        # Update the response below to pull the token from the correct key
        return response.get('token', None)

    def _request(self, url, method="GET", data=None):
        """
        Make a request to the REST API
        :param url: The URL to request
        :param method: The HTTP method to use
        :param data: The data to send with the request
        """
        r = requests.request(
            method,
            url,
            headers=self.headers,
            json=data,
            verify=self.verify,
        )

        # Inject your own error handling of the response below:
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(f'Error encountered for URL: {url}, details: '
                         f'{e.response.content}')
            raise e
        # You can either return the entire response object or just the JSON
        # response - I typically prefer to have the JSON object returned
        return r.json()

    def wait_for_complete(self, job_id):
        """
        Some systems return asynchronous jobs that need to be waited on. This is
        a simple example of how to wait for a job to complete. Edit to suit your
        needs.
        :param job_id: ID of the job
        :return:
        """
        # The job_type is singular, have to add an 's' to the url
        url = f'{self.base_url}/jobs/{job_id}/'
        status = 'pending'
        while status in ['pending', 'waiting', 'running']:
            response = self.get(url)
            status = response.get('status', None)
            set_progress(f'Ansible Automation: Job ID: {job_id} Status: '
                         f'{status}')
            if status in ['successful', 'failed']:
                # logger.debug(f'response_json: {json.dumps(response.json())}')
                result = response.get('result_stdout', None)
                set_progress(result)
                return status, response
            else:
                time.sleep(10)
