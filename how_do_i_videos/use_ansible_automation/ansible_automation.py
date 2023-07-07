"""
Ansible Automation Ad-Hoc Job Template
This action allows you to invoke an Ansible Automation Job Template via
CloudBolt

1. Allow the selection of an Ansible Automation Connection Info and Job Template
   in the blueprint
2. Capture any outputs written in Ansible via set_stats or set_facts - write
   these back to the CloudBolt resource as parameters

Setup:
- Connection Info: Create a Connection Info and label it as "ansible_automation"
    - For BASIC Auth scenarios, include the user and password in the Connection
        Info. Be sure that AUTH_TYPE is set to "BASIC" in the script.
    - For OAUTH2 scenarios, include the OAUTH2 token in the Connection Info in
        the password field. Be sure that AUTH_TYPE is set to "OAUTH2" in the
- Ansible template should have the following options enabled:
    Enabled Concurrent Jobs: True (Checked)
    Limit: PROMPT ON LAUNCH = True (Checked)
    Extra Variables: PROMPT ON LAUNCH = True (Checked)
- CloudBolt Blueprint should have this action under the "Build" Tab.
- It is recommended to set default values for each of the following parameters
  under the build tab.
    - ansible_automation: Default value for Ansible Automation
    - ansible_template_id: Default value for Ansible Template ID
    - template_type: Default value for Template Type
- On the blueprint add Parameters for each extra var that needs to be passed
  for the job template. The parameter name should be prepended with extra_var_
"""
from resources.models import Resource
from common.methods import set_progress
from utilities.models import ConnectionInfo
from infrastructure.models import CustomField
import requests
import json
import time
import base64
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

# Auth Type can be either "OAUTH2" or "BASIC" - BASIC would be used in the case
# Where OAUTH2 Tokens are not allowed - one use case would be for external
# accounts such as LDAP.
AUTH_TYPE = "BASIC"
ASK_LIMIT_ON_LAUNCH = False


def run(job=None, logger=None, server=None, resource=None, **kwargs):
    ansible_template_id = "{{ ansible_template_id }}"
    conn_info_id = "{{ ansible_automation }}"
    template_type = "{{ template_type }}"
    extra_vars = eval("{{extra_vars}}")[0]

    if template_type not in ["workflow_job_templates", "job_templates"]:
        raise Exception(f"template_type is not equal to either "
                        f"workflow_job_template, or job_template.")
    if not template_type:
        raise Exception(f"template_type is not set for plugin")
    logger.debug(f'Extra Vars: {extra_vars}')
    aa = AnsibleAutomation(conn_info_id, AUTH_TYPE)
    launch_url = aa.get_launch_url(ansible_template_id, template_type)
    status, response_json = aa.run_template(launch_url, extra_vars)
    aa.write_artifacts_to_resource(response_json, resource, template_type)

    if status != 'successful':
        msg = "Ansible Automation: Job Failed"
        return "FAILURE", "", msg
    else:
        return "SUCCESS", "", ""


def generate_options_for_ansible_automation(field=None, **kwargs):
    conn_infos = ConnectionInfo.objects.filter(
        labels__name='ansible_automation')
    return [(ci.id, ci.name) for ci in conn_infos]


def generate_options_for_template_type(field=None, **kwargs):
    return ["job_templates", "workflow_job_templates"]


"""
Sample code for generating options for Ansible Templates based on the
Ansible Automation selected. This code is not used in the action, but is 
provided as an example of how to generate options for a field based on the value
of another field. You would also need to remove "comment" from the method name. 
def generate_options_for_comment_ansible_template_id(field=None,
                                             control_value_dict=None,
                                             **kwargs):
    logger.info(f'control_value: {control_value_dict}')
    if not control_value_dict:
        return [("", "First Select Ansible Automation and Job Type")]
    if not (control_value_dict['ansible_automation'] and
            control_value_dict['template_type']):
        return [("", "First Select Ansible automation and Job Type")]
    logger.info(f'control_value: {control_value_dict}')
    template_type = control_value_dict['template_type']
    aa_id = control_value_dict['ansible_automation']
    aa = AnsibleAutomation(aa_id, "BASIC")
    templates = aa.get_all_templates(template_type)
    return [(t['id'], t['name']) for t in templates]
"""


def get_ansible_extra_vars(resource):
    extra_vars = {}
    for key, value in resource.get_cf_values_as_dict().items():
        if key.find('extra_var_') == 0:
            stripped_key = key.replace('extra_var_', '')
            extra_vars[stripped_key] = value
    return str(extra_vars)


class AnsibleAutomation(object):
    """
    Wrapper for the Ansible Automation REST API.

    To use this class:
    1. Create a ConnectionInfo object with the following fields:
        - name: A name for the connection info
        - protocol: http or https
        - ip: The IP address or Hostname of the Ansible Automation Controller
        - port: The port of the Ansible Automation Controller
        - username: The username to use for the connection (not needed for
          OAUTH)
        - password: The password to use for the connection or token for the user
          if using OAUTH
    2. Create an instance of this class with the name of the ConnectionInfo
    object:
        aa = AnsibleAutomation(<ansible_id>, "BASIC")
    3. Use the methods of this class to make requests to the Ansible Automation
       REST API:
        aa.get_all_templates('job_templates')
    """

    def __init__(self, conn_info_id, auth_type='BASIC'):
        """
        :param conn_info_id: The name of the ConnectionInfo object to use
        :param auth_type: The type of authentication to use. Either "OAUTH2" or
            "BASIC". Defaults to "BASIC"
        """
        self.conn_info = ConnectionInfo.objects.get(id=conn_info_id)
        self.root_url = f'{self.conn_info.protocol}://{self.conn_info.ip}'
        if self.conn_info.port:
            self.root_url = f'{self.root_url}:{self.conn_info.port}'
        self.base_url = f'{self.root_url}/api/v2'
        self.verify = False
        self.auth_type = auth_type
        self.headers = self.get_headers()

    def get(self, url):
        return self._request(url)

    def post(self, url, data):
        return self._request(url, method="POST", data=data)

    def patch(self, url, data):
        return self._request(url, method="PATCH", data=data)

    def put(self, url, data):
        return self._request(url, method="PUT", data=data)

    def delete(self, url, data=None):
        return self._request(url, method="DELETE", data=data)

    def get_headers(self):
        """
        Set the headers for the Ansible Automation API
        """
        if self.auth_type == "OAUTH2":
            return {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.conn_info.password}'
            }
        elif self.auth_type == "BASIC":
            creds = f'{self.conn_info.username}:{self.conn_info.password}'
            base_64 = base64.b64encode(f'{creds}'.encode("ascii")).decode(
                'ascii')
            return {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {base_64}'
            }
        else:
            raise Exception("auth_type must be either OAUTH2 or BASIC")

    def _request(self, url, method="GET", data=None):
        """
        Return the json of a Request to the Ansible Automation API
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

        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(f'Error encountered for URL: {url}, details: '
                         f'{e.response.content}')
            raise e
        return r.json()

    def get_all_templates(self, template_type):
        """
        Get all templates from Ansible Automation
        :param template_type: either "job_templates" or "workflow_job_templates"
        :return:
        """
        if template_type not in ["job_templates", "workflow_job_templates"]:
            raise Exception(f"template_type must be either job_templates or "
                            f"workflow_job_templates, not {template_type}")
        url = f'{self.base_url}/{template_type}/'
        logger.debug(f'templates_url: {url}')
        response_json = self.get(url)
        templates = []
        all_results = response_json.get('results', None)
        next_page = response_json.get("next")
        while next_page:
            next_url = f'{self.root_url}{next_page}'
            response_json = self.get(next_url)
            results = response_json.get('results', None)
            all_results += results
            next_page = response_json.get("next")

        for r in all_results:
            # Include all templates if ASK_LIMIT_ON_LAUNCH is false, if not check
            # the job template for prompt on launch for limit
            if ASK_LIMIT_ON_LAUNCH:
                ask_limit_on_launch = r.get('ask_limit_on_launch', None)
                if not ask_limit_on_launch:
                    continue
            templates.append(r)
        logger.debug(f'templates: {templates}')
        return templates

    def get_launch_url(self, template_id, template_type):
        """
        Get the launch url of a template from Ansible Automation
        :param template_id:
        :param template_type:
        :return:
        """
        if template_type not in ["job_templates", "workflow_job_templates"]:
            raise Exception(f"template_type must be either job_templates or "
                            f"workflow_job_templates, not {template_type}")
        url = f'{self.base_url}/{template_type}/{template_id}/'
        response = self.get(url)
        logger.debug(f'response: {response}')
        related = response.get('related', None)
        launch = None
        if related:
            related = response['related']
            launch = related.get('launch', None)
        if not launch:
            raise Exception(f'No launch url found for template_id: '
                            f'{template_id}')
        return launch

    def run_template(self, launch_url: str, extra_vars: dict = {},
                     inventory: str = None, credential: str = None,
                     limit: str = None):
        """
        Run a template from Ansible Automation
        :param launch_url: Launch URL of the template
        :param extra_vars: Dictionary of extra vars to pass to the template
        :return:
        """
        url = f'{self.root_url}{launch_url}'
        params = {"extra_vars": ""}
        if extra_vars:
            params['extra_vars'] = extra_vars
        if inventory:
            params['inventory'] = inventory
        if credential:
            params['credential'] = credential
        if limit:
            params['limit'] = limit
        set_progress('Ansible Automation: Launching Job Template')
        """
        set_progress('Ansible Automation: Template Params: {}'.format(params))
        set_progress(f'HEADERS: {HEADERS}')
        set_progress(f'url: {url}')
        """
        response = self.post(url, params)
        logger.debug(f'response: {response}')
        job_type = response["type"]
        set_progress(f'Ansible Automation: Job Type: {job_type}')
        job_id = response[job_type]
        status, response_json = self.wait_for_complete(job_id, job_type)
        return status, response_json

    def wait_for_complete(self, job_id, job_type):
        """
        Wait for a job to complete
        :param job_id: ID of the job
        :param job_type: Type of the job
        :return:
        """
        # The job_type is singular, have to add an 's' to the url
        url = f'{self.base_url}/{job_type}s/{job_id}/'
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

    def get_job_events_facts(self, response_json):
        """
        Get the facts from an Ansible Automation job response
        :param response_json: Response from Ansible Automation job
        :return:
        """
        try:
            events_page = response_json["related"]["job_events"]
            events_url = f'{self.root_url}{events_page}'
        except KeyError:
            return None
        facts = {}
        response_json = self.get(events_url)
        facts = self.add_facts_to_list(response_json, facts)
        next_page = response_json["next"]
        while next_page:
            next_url = f'{self.root_url}{next_page}'
            response_json = self.get(next_url)
            facts = self.add_facts_to_list(response_json, facts)
            next_page = response_json["next"]
        return facts

    @staticmethod
    def add_facts_to_list(response_json, facts):
        for result in response_json["results"]:
            try:
                if result["event"] == "runner_on_ok":
                    event_data = result["event_data"]
                    if event_data["task_action"] == "set_fact":
                        ansible_facts = event_data["res"]["ansible_facts"]
                        for key in ansible_facts.keys():
                            facts[key] = ansible_facts[key]
            except KeyError as e:
                logger.warning(f'Error encountered gathering facts. Error: {e}')
        return facts

    def write_artifacts_to_resource(self, response_json, resource: Resource,
                                    template_type):
        """
        Write the artifacts from an Ansible Automation job response to a
        CloudBolt resource
        :param response_json: Response from Ansible Automation job
        :param resource: CloudBolt resource to write the artifacts to
        :return:
        """
        if template_type == "workflow_job_template":
            nodes = response_json["related"]["workflow_nodes"]
            nodes_url = f'{self.root_url}{nodes}'
            response_json = self.get(nodes_url)
            for result in response_json["results"]:
                job = result["related"]["job"]
                job_url = f'{self.root_url}{job}'
                job_json = self.get(job_url)
                self.write_job_artifacts_to_resource(job_json, resource)
        else:
            self.write_job_artifacts_to_resource(response_json, resource)

    def write_job_artifacts_to_resource(self, job_json, resource: Resource):
        artifacts = job_json["artifacts"]
        job_events_facts = self.get_job_events_facts(job_json)
        facts = {**artifacts, **job_events_facts}
        if facts:
            # logger.debug(f'Writing facts to Server. Facts: {facts}')
            for key in facts.keys():
                cf_name = f'ansible_artifact_{key}'
                cf_value = facts[key]
                if type(cf_value) == dict:
                    cf_value = json.dumps(cf_value)
                    logger.debug(f"cf_value for {key} was dict")
                description = "Created by Ansible Artifacts"
                defaults = {
                    "label": key,
                    "description": description,
                    "show_on_servers": True
                }
                cf, _ = CustomField.objects.get_or_create(
                    name=cf_name, type="STR", defaults=defaults
                )
                resource.set_value_for_custom_field(cf_name, cf_value)
