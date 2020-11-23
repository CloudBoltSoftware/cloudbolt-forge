import requests
import json
import re
import ast
import adal
from utilities.models import ConnectionInfo
from infrastructure.models import CustomField

'''
From Azure AD, grant application API access to Microsoft graph - Application permission ->
Grant DirectoryReadAll and DirectoryReadWriteAll
'''

CI = ConnectionInfo.objects.get(name='Office365')
assert isinstance(CI, ConnectionInfo)

firstname = '{{ first_name }}'
lastname = '{{ last_name }}'
userpass = '{{ user_password }}'

'''
Get MS Graph connection info. Create a connection info in CB with Client ID and Secret Id of Azure web app,
resource and url should be 'graph.microsoft.com'.
Admin -> ConnectionInfo -> 'New Connection Info'
'''
authority = 'https://login.microsoftonline.com/'
resource_ = f'{CI.protocol}://{CI.ip}'
url = f'{CI.protocol}://{CI.ip}:{CI.port}/v1.0/users/'

headers = ast.literal_eval(CI.headers)

tenant_id = headers.get('tenant_id')
client_id = headers.get('client_id')
client_secret = headers.get('client_secret')


def run(resource, **kwargs):
    create_custom_fields()
    if userpass is not None:
        pattern = r"^((?=.*[a-z])(?=.*[A-Z])(?=.*\d)|(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9])|(?=.*[a-z])(?=.*\d) \
            (?=.*[^A-Za-z0-9])|(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]))([A-Za-z\d@#$%^&£*\-_+=[\]{}|\\:',?/`~\"();!]|\.(?!@)){8,123}$"
        if not re.match(pattern, userpass):
            return (
                "FAILURE",
                "Please provide a complex password (8-123 chars, upper/lowercase, numbers, special characters)", "")

    context = adal.AuthenticationContext(authority + tenant_id)
    token = context.acquire_token_with_client_credentials(resource_, client_id, client_secret)
    _headers = {'Authorization': 'Bearer {0}'.format(token['accessToken']), 'Content-Type': 'application/json'}
    domain = requests.get(url, headers=_headers).json().get('value')[0].get('userPrincipalName').split('@')[-1]

    userPrincipalName = f'{firstname}@{domain}'.lower()
    body = {
        "accountEnabled": 'true',
        "displayName": f'{firstname} {lastname}',
        "mailNickname": f'{firstname}{lastname}'.lower(),
        "userPrincipalName": userPrincipalName,
        "passwordProfile": {
            "forceChangePasswordNextSignIn": 'true',
            "password": userpass,
        }
    }

    response = requests.post(url, headers=_headers, data=json.dumps(body), params=None)
    if not response.ok:
        return "FAILURE", f"{response.json()}", ""

    resource.first_name = firstname
    resource.last_name = lastname
    resource.name = firstname + ' ' + lastname
    resource.userPrincipalName = userPrincipalName
    resource.user_id = response.json().get('id')
    resource.save()
    return "SUCCESS", "User account {[0]}{}@{} created".format(firstname, lastname, domain).lower(), ""


def create_custom_fields():
    CustomField.objects.get_or_create(
        name='first_name', type='STR',
        defaults={'label': 'first name', 'description': 'Used by the Office 365 blueprints', 'show_as_attribute': True})
    CustomField.objects.get_or_create(
        name='last_name', type='STR',
        defaults={'label': 'last name', 'description': 'Used by the Office 365 blueprints', 'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='userPrincipalName', type='STR',
        defaults={'label': 'User Principal Name', 'description': 'Used by the Office 365 blueprints',
                  'show_as_attribute': True}
    )
    CustomField.objects.get_or_create(
        name='user_id', type='STR',
        defaults={'label': 'ID', 'description': 'Used by the Office 365 blueprints', 'show_as_attribute': True}
    )
