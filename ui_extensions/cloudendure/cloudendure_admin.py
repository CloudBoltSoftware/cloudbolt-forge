import base64
import requests
import json
from common.methods import generate_string_from_template
from utilities.models import ConnectionInfo
from c2_wrapper import create_hook


class CloudEndureManager:
    def __init__(self):
        ci = ConnectionInfo.objects.filter(
            name__iexact='CloudEndure Endpoint').first()
        self.connection_info = ci
        self.endpoint = '/api/latest/{}'

    def verify_connection(self, proto=None, ip=None, username=None, port=None, password=None):
        if proto and ip and username and password and port:
            ci = ConnectionInfo(name="test", protocol=proto, port=port,
                                ip=ip, username=username, password=password)
        else:
            ci = self.get_connection_info()

        if self.verify_credentials(ci)[0]:
            return True
        return False

    def get_auth(self):
        ci = self.get_connection_info()
        headers = {'Content-Type': 'application/json'}
        session = {}
        try:
            # obtain a session, and required headers
            response = requests.post(ci.format_url() + self.endpoint.format('login'), data=json.dumps(
                {'username': ci.username, 'password': ci.password}), headers=headers)

            session = {'session': response.cookies['session']}
            headers['X-XSRF-TOKEN'] = response.cookies['XSRF-TOKEN']
            return session, headers
        except Exception:
            return session, headers

    def verify_credentials(self, ci):
        if not ci:
            return False, "No Connection Info found"
        endpoint = '/api/latest/login'
        session = requests.Session()
        session.headers.update(
            {'Content-type': 'application/json', 'Accept': 'text/plain'})
        try:
            response = session.post(url=ci.format_url() + endpoint, data=json.dumps(
                {'username': ci.username, 'password': ci.password}))
        except Exception as error:
            return False, str(error)
        return response.ok, response.reason

    def get_connection_info(self):
        return self.connection_info

    def get_all_projects(self, more_info=False):
        ci = self.get_connection_info()
        session, headers = self.get_auth()
        try:
            # fetch all projects
            projects = requests.get(
                ci.format_url() + self.endpoint.format('projects'), headers=headers, cookies=session)
            if more_info:
                returned_data = []
                for project in projects.json().get('items'):
                    properties = {}
                    properties['name'] = project['name']
                    properties['id'] = project['id']
                    properties['type'] = project['type']
                    properties['agentInstallationToken'] = project['agentInstallationToken']
                    returned_data.append(properties)
                return returned_data
            else:
                return [x['name'] for x in projects.json().get('items')]
        except Exception:
            return []

    def get_agent_installation_token(self, project_name):
        ci = self.get_connection_info()
        try:
            session, headers = self.get_auth()
            # fetch all projects, and return the desired installation token
            projects = requests.get(
                ci.format_url() + self.endpoint.format('projects'), headers=headers, cookies=session)
            return [project['agentInstallationToken'] for project in projects.json().get('items') if project['name'] == project_name]
        except Exception as error:
            return None, str(error)

    def execute_script(self, template, context, server):
        template = generate_string_from_template(template=template,
                                                 group=None, env=None,
                                                 os_build=None, context=context)
        result = server.execute_script(script_contents=template, timeout=1200)
        return result

    def install_agent(self, template, context, server):
        install_agent_result = self.execute_script(template, context, server)
        return install_agent_result

    def check_agent_status(self, server):
        ci = self.get_connection_info()
        try:
            session, headers = self.get_auth()
            # fetch all projects and machines, and return the names of all machines
            projects = requests.get(
                ci.format_url() + self.endpoint.format('projects'), headers=headers, cookies=session)

            project_ids = [project['id']
                           for project in projects.json().get('items')]

            names = []
            for project_id in project_ids:
                machines = requests.get(ci.format_url() + self.endpoint.format(
                    'projects/{}/machines').format(project_id), headers=headers, cookies=session)

                for machine in machines.json()['items']:
                    names.append(machine['sourceProperties']['name'])

            # for windows machines, cloudednure truncates hostname to only the first fifteen characters.
            if server.is_windows():
                hostname = server.hostname[:15]
            else:
                hostname = server.hostname
            if hostname in names:
                return True, "Agent has been installed in this server"
            else:
                return False, "Agent has not been installed in this server"
        except Exception as error:
            return False, str(error)

    def replication_actions(self, server, action, **kwargs):
        ci = self.get_connection_info()
        project = server.cloud_endure_project
        try:
            session, headers = self.get_auth()

            # get our project_id
            projects = requests.get(
                ci.format_url() + self.endpoint.format('projects'), headers=headers, cookies=session)

            project_id = [project_name['id'] for project_name in projects.json().get(
                'items') if project_name['name'] == project][0]

            if server.is_windows():
                hostname = server.hostname[:15]
            else:
                hostname = server.hostname

            # get the desired machine
            machines = requests.get(ci.format_url() + self.endpoint.format(
                'projects/{}/machines').format(project_id), headers=headers, cookies=session)
            machine_id = [machine['id'] for machine in machines.json().get(
                'items') if machine['sourceProperties']['name'] == hostname]

            if action == 'start':
                # start replication of the specified machine
                start_response = requests.post(ci.format_url() + self.endpoint.format(
                    'projects/{}/startReplication').format(project_id), headers=headers, cookies=session, json={"machineIDs": machine_id})

                if start_response.status_code == 200:
                    return True, "Request to start replication acknowledged."

            elif action == 'pause':
                # pause replication of the specified machine
                pause_response = requests.post(ci.format_url() + self.endpoint.format(
                    'projects/{}/pauseReplication').format(project_id), headers=headers, cookies=session, json={"machineIDs": machine_id})

                if pause_response.status_code == 200:
                    return True, "Replication paused succesfully"

            elif action == 'stop':
                # stop replication of the specified machine
                stop_response = requests.post(ci.format_url() + self.endpoint.format(
                    'projects/{}/stopReplication').format(project_id), headers=headers, cookies=session, json={"machineIDs": machine_id})

                if stop_response.status_code == 200:
                    return True, "Request to stop replication acknowledged."
                elif stop_response.status_code == 409:
                    return False, "Another job is already running in this project."
                elif stop_response.status_code == 429:
                    return False, "Too many jobs are running for this project."

            elif action == 'uninstall':
                # uninstall agent from this server
                uninstall_response = requests.delete(ci.format_url() + self.endpoint.format(
                    'projects/{}/machines').format(project_id), headers=headers, cookies=session, json={"machineIDs": machine_id})

                if uninstall_response.status_code == 204:
                    return True, "Machine removed from CloudEndure service."

            elif action == 'migrate':
                response = self.launch_machine(
                    project_id, machine_id[0], kwargs.get('launch_type'))
                if response[0] == 202:
                    return True, response[1]
                else:
                    return False, response[1]

        except Exception as error:
            return False, str(error)

    def get_all_servers(self):
        ci = self.get_connection_info()
        try:
            session, headers = self.get_auth()

            # fetch all projects, and return the desirede installation token
            projects = requests.get(
                ci.format_url() + self.endpoint.format('projects'), headers=headers, cookies=session)
            project_ids = [project['id'] for project in projects.json().get(
                'items')]

            # fetch all machines
            machine_properties = []
            for project_id in project_ids:
                machines = requests.get(ci.format_url() + self.endpoint.format(
                    'projects/{}/machines').format(project_id), headers=headers, cookies=session)

                for machine in machines.json()['items']:
                    properties = {}
                    properties['name'] = machine['sourceProperties']['name']
                    properties['id'] = machine['id']
                    properties['project_id'] = project_id

                    machine_properties.append(properties)
            return machine_properties

        except Exception:
            return []

    def launch_machine(self, project_id, machine_id, launch_type):
        session, headers = self.get_auth()
        ci = self.get_connection_info()
        url = ci.format_url() + self.endpoint.format('projects/{}/launchMachines').format(project_id)
        data = {"launchType": launch_type, "items": [
            {"machineId": machine_id}]}
        response = requests.post(url, headers=headers,
                                 cookies=session, json=data)
        machine_name = requests.get(ci.format_url(
        ) + self.endpoint.format('projects/{}/machines/{}').format(project_id, machine_id), headers=headers,
            cookies=session)
        if response.status_code == 202:
            return response.status_code, f"{launch_type} job created for {machine_name.json().get('sourceProperties').get('name')}. Check the jobs tab and refresh to get the jobs progress."
        elif response.status_code == 400:
            return response.status_code, "Another job is already running in this project."
        elif response.status_code == 402:
            return response.status_code, "Project license has expired."
        else:
            return response, "There was an unexpected error while trying to migrate"

    def get_cloud_credentials(self):
        session, headers = self.get_auth()
        response = requests.get(self.connection_info.format_url() +
                                self.endpoint.format('cloudCredentials'), headers=headers, cookies=session)
        return [credentials['id'] for credentials in response.json().get('items')]

    def get_all_jobs(self):
        session, headers = self.get_auth()
        all_jobs = []
        projects = self.get_all_projects(more_info=True)
        for project in projects:
            response = requests.get(self.connection_info.format_url() + self.endpoint.format(
                'projects/{}/jobs').format(project['id']), headers=headers, cookies=session)
            jobs = response.json().get('items')
            for job in jobs:
                job_details = {}
                job_details['status'] = job['status']
                job_details['participatingMachines'] = job['participatingMachines'][0]
                job_details['type'] = job['type']
                job_details['id'] = job['id']
                if job.get('endDateTime'):
                    job_details['endDateTime'] = job['endDateTime'].split(
                        'T')[0] + " " + job['endDateTime'].split('T')[1][:8]
                else:
                    job_details['endDateTime'] = "N/A"
                job_details['creationDateTime'] = job['creationDateTime'].split(
                    'T')[0] + " " + job['creationDateTime'].split('T')[1][:8]
                all_jobs.append(job_details)
        return all_jobs

    def get_all_clouds(self):
        try:
            session, headers = self.get_auth()
            response = requests.get(self.connection_info.format_url() +
                                    self.endpoint.format('clouds'), headers=headers, cookies=session)
            return [(cloud['id'], cloud['name']) for cloud in response.json().get('items') if cloud['name'] == 'AWS']
        except Exception:
            return []


    def create_project(self, name, cloud_id, public_key, private_key):
        ci = self.get_connection_info()
        session, headers = self.get_auth()
        encoded_private_key = base64.b64encode(private_key.encode()).decode("utf-8")

        credentials_body = {"publicKey": public_key,"privateKey": encoded_private_key,"cloudId":cloud_id}

        cloud_credentials_response = requests.post(ci.format_url() + self.endpoint.format('cloudCredentials'), headers=headers, cookies=session, json=credentials_body)
        try:
            cloudCredentialsIDs = cloud_credentials_response.json().get('id')
        except Exception:
            cloudCredentialsIDs = ""

        projects_body = {"name": name,"type": "MIGRATION","targetCloudId": cloud_id, "cloudCredentialsIDs": [cloudCredentialsIDs]}
        response = requests.post(ci.format_url() +self.endpoint.format('projects'), headers=headers, cookies=session, json=projects_body)
        return response

    def setup_cloud_endure_install_agent_action(self):
        cloud_endure_hook = {
            'name': "Install CloudEndure Agent",
            'description': "Installs CloudEndure Agent on a Server",
            'hook_point': None,
            'module': '/var/opt/cloudbolt/proserv/xui/cloudendure/install_agent.py',
        }
        create_hook(**cloud_endure_hook)
