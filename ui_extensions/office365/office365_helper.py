import adal
import requests
import ast

from utilities.models import ConnectionInfo


class Office365Manager:
    def __init__(self, connection_info=None):
        self.authority = 'https://login.microsoftonline.com/'
        self.connection_info = self.get_connection_info(connection_info)
        self.resource_ = '{}://{}'.format(self.connection_info.protocol, self.connection_info.ip)
        self.users_url = self.get_users_url(self.connection_info.protocol, self.connection_info.ip,
                                            self.connection_info.port)

    @staticmethod
    def get_connection_info(ci=None):
        if ci:
            return ci
        return ConnectionInfo.objects.filter(name__iexact='Office365').first()

    def get_users_url(self, protocol, ip, port):
        return f"{protocol}://{ip}:{port}/v1.0/users/"

    def get_tenant_id(self):
        ci = self.get_connection_info()
        headers = ast.literal_eval(ci.headers)
        return headers.get('tenant_id')

    def get_client_id(self):
        ci = self.get_connection_info()
        headers = ast.literal_eval(ci.headers)
        return headers.get('client_id')

    def get_client_secret(self):
        ci = self.get_connection_info()
        headers = ast.literal_eval(ci.headers)
        return headers.get('client_secret')

    def verify_credentials(self, protocol, ip, port, headers):
        url = self.get_users_url(protocol, ip, port)
        headers = ast.literal_eval(headers)
        tenant_id = headers.get('tenant_id')
        client_id = headers.get('client_id')
        client_secret = headers.get('client_secret')

        if not tenant_id:
            return False, "tenant_id is not supplied"

        if not client_id:
            return False, "client_id is not supplied"

        if not client_secret:
            return False, "client_secret is not supplied"
        try:
            context = adal.AuthenticationContext(self.authority + tenant_id)
            token = context.acquire_token_with_client_credentials(self.resource_, client_id, client_secret)
        except Exception as error:
            return False, error

        _headers = {'Authorization': 'Bearer {0}'.format(token['accessToken']), 'Content-Type': 'application/json'}

        response = requests.get(url, headers=_headers)
        return response.ok, response.reason
