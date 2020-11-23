from utilities.models import ConnectionInfo

import requests

API_CLIENT_CI = "Citrix API"


def get_citrix_url():
    ci = ConnectionInfo.objects.get(name=API_CLIENT_CI)
    return "{protocol}://{hostname}".format(protocol=ci.protocol, hostname=ci.ip)


def get_citrix_api_token():
    # Citrix api uses tokens to authorise requests. The tokens expires after a short while and has to be regenerated.
    ci = ConnectionInfo.objects.get(name=API_CLIENT_CI)
    url = get_citrix_url()
    response = requests.get(
        "{url}/api/oauth/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials".format(
            url=url, client_id=ci.username, client_secret=ci.password))
    token = response.json().get('access_token')

    return token


def run(resource, *args, **kwargs):
    url = "https://portal.cedexis.com:443/api/v2/config/authdns.json/record/{}".format(resource.record_id)
    token = get_citrix_api_token()
    value = "{{ value }}"

    if not token:
        return "FAILURE", "", "No token Authorization Token. Ensure you have set up your credentials on the " \
                              "connection info page "
    head = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

    response = requests.delete(url=url, headers=head)
    if response.ok:
        return "SUCCESS", "Sample output message", ""
    else:
        return "FAILURE", "", "{}".format(response.json().get('errorDetails')[0].get('developerMessage'))
