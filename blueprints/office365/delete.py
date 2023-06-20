"""
Delete office 365 user
"""
import requests
import ast
import adal
from utilities.models import ConnectionInfo
from common.methods import set_progress


def run(**kwargs):
    set_progress("Deleting office365 user...")
    resource = kwargs.pop('resources').first()
    CI = ConnectionInfo.objects.get(name='Office365')
    authority = 'https://login.microsoftonline.com/'
    resource_ = f'{CI.protocol}://{CI.ip}'
    url = f'{CI.protocol}://{CI.ip}:{CI.port}/v1.0/users/{resource.user_id}'
    headers = ast.literal_eval(CI.headers)

    tenant_id = headers.get('tenant_id')
    client_id = headers.get('client_id')
    client_secret = headers.get('client_secret')

    context = adal.AuthenticationContext(authority + tenant_id)
    token = context.acquire_token_with_client_credentials(resource_, client_id, client_secret)
    headers = {'Authorization': 'Bearer {0}'.format(token['accessToken']), 'Content-Type': 'application/json'}

    response = requests.delete(url, headers=headers)
    if response.ok:
        return "SUCCESS", "", ""

    return "FAILURE", f"{response.reason}", ""
