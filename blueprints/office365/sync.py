import requests
import ast
import adal
from utilities.models import ConnectionInfo
from common.methods import set_progress
from infrastructure.models import CustomField

RESOURCE_IDENTIFIER = "userPrincipalName"


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


def discover_resources(**kwargs):
    create_custom_fields()
    discovered_users = []

    set_progress("Discovering office365 users...")
    CI = ConnectionInfo.objects.get(name='Office365')
    headers = ast.literal_eval(CI.headers)

    authority = 'https://login.microsoftonline.com/'
    resource_ = '{}://{}'.format(CI.protocol, CI.ip)
    url = f'{CI.protocol}://{CI.ip}:{CI.port}/v1.0/users/'

    tenant_id = headers.get('tenant_id')
    client_id = headers.get('client_id')
    client_secret = headers.get('client_secret')

    context = adal.AuthenticationContext(authority + tenant_id)
    token = context.acquire_token_with_client_credentials(resource_, client_id, client_secret)
    headers = {'Authorization': 'Bearer {0}'.format(token['accessToken']), 'Content-Type': 'application/json'}

    response = requests.get(url, headers=headers)
    if response.ok:
        users = response.json().get('value')
        set_progress(f"Discovered {len(users)} office365 users.")
        for user in users:
            discovered_users.append({
                "name": user.get('displayName'),
                "first_name": user.get('surname'),
                "last_name": user.get('givenName'),
                'userPrincipalName': user.get('userPrincipalName'),
                'user_id': user.get('id')
            })
        return discovered_users
    set_progress("Error occured while trying to discover users")
    return []
