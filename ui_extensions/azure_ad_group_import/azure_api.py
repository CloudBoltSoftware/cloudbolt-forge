import requests
from msal import ConfidentialClientApplication
import logging

logger = logging.getLogger(__name__)


def get_access_token(client_id, client_secret, tenant_id):
    app = ConfidentialClientApplication(
        client_id=client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        logger.error("Token acquisition failed: %s", result)
        raise Exception(result)
    return result["access_token"]


def fetch_all_groups(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://graph.microsoft.com/v1.0/groups?$top=100"
    all_groups = []

    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        all_groups.extend(data.get("value", []))
        url = data.get("@odata.nextLink")

    return all_groups


def get_group_by_id(group_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/groups/{group_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
