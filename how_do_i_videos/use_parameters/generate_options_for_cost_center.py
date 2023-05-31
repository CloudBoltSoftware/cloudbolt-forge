import requests
from utilities.models.models import ConnectionInfo
from utilities.logger import ThreadLogger

logger = ThreadLogger("Service Now Generate Options")


def get_options_list(field, **kwargs):
    """
    A working sample that returns a dynamically generated list of options.

    :param field: The field you are generating options for (of type CustomField or its subclass HookInput).

    See the "Generated Parameter Options" section of the docs for more info and the CloudBolt forge
    for more examples: https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
    """
    conn_info_name = "servicenow"
    conn = ConnectionInfo.objects.get(name=conn_info_name)
    username = conn.username
    password = conn.password
    base_url = f"{conn.protocol}://{conn.ip}"
    table = "cmn_cost_center"

    # Otherwise, define the database values and labels as a list of 2-tuples.
    url = f'{base_url}/api/now/table/{table}'
    response = requests.get(
        url=url,
        auth=(username, password),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=5.0
    )

    options = [("", "------Please Select a Cost Center------")]
    for result in response.json()['result']:
        options.append((result["account_number"], result["name"]))

    return {
        'options': options,
    }