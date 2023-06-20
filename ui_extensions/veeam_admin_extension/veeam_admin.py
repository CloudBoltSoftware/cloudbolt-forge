'''
# Python class for all veeam admin related tasks
You must have a connectionInfo object defined in cloudbolt
'''

import base64
import requests

from common.methods import generate_string_from_template
from utilities.models import ConnectionInfo, GlobalPreferences
from xui.veeam.veeam_scripts import CHECK_VM
from utilities.logger import ThreadLogger
from c2_wrapper import create_hook

logger = ThreadLogger(__name__)


class VeeamManager(object):
    def __init__(self):
        ci = ConnectionInfo.objects.filter(
            name__iexact='Veeam Server Management Endpoint').first()
        self.connection_info = ci
        self.session_id = None
        self.jobs = []
        self.ip_or_names = []
        self.backup_resources = []
        self.discovered_vm_restore_points = []
        self.backup_servers = []
        self.total_jobs = []
        self.total_backups = []
        self.agent_jobs = []
        self.create_custom_fields_as_needed()
        gp = GlobalPreferences.objects.first()
        self.verify_ssl_checks = gp.enable_ssl_verification

    def verify_connection(self, proto=None, ip=None, port=None, username=None, password=None):
        if proto and ip and port and username and password:
            ci = ConnectionInfo(name="test", protocol=proto, ip=ip,
                                port=port, username=username, password=password)
        else:
            ci = self.get_connection_info()

        # no exceptions means success
        self.get_session_id(ci)

        # Remove all caches while verifying connection.
        self.jobs = []
        self.ip_or_names = []
        self.backup_resources = []
        self.discovered_vm_restore_points = []
        self.backup_servers = []
        self.total_jobs = []
        self.total_backups = []
        self.agent_jobs = []

    def get_connection_info(self):
        return self.connection_info

    def get_session_id(self, connection_info=None):
        if self.session_id:
            return
        if not connection_info:
            connection_info = self.connection_info
        if not connection_info:
            return None
        url = connection_info.format_url(
            auth=False) + '/api/sessionMngr/?v=latest'
        encoded_credentials = base64.b64encode(
            (connection_info.username + ':' + connection_info.password).encode())
        headers = {"Authorization": "Basic {credentials}".format(
            credentials=encoded_credentials.decode())}
        response = requests.post(url, headers=headers, verify=self.verify_ssl_checks)
        if response.status_code == 401:
            # credentials are invalid.
            raise Exception("Invalid Username or password")
        session_id = response.headers.get('X-RestSvcSessionId')
        self.session_id = session_id

    def api_get(self, url):
        if not self.session_id:
            self.get_session_id(self.connection_info)
        if url.startswith("http"):
            uri = url
        else:
            uri = "/".join([self.connection_info.format_url(auth=False), url])
        header = {'X-RestSvcSessionId': self.session_id,
                  'Accept': "Application/json"}
        return requests.get(url=uri, headers=header, verify=self.verify_ssl_checks)

    def get_jobs(self):
        if self.jobs:
            return self.jobs
        if not self.connection_info:
            return []
        resources = []
        jobs = self.api_get("/api/jobs")
        agent_jobs = self.api_get("/api/agents/jobs")

        for job in jobs.json()['Refs']:
            resources.append({'name': job['Name'], 'id': job['UID']})
        for job in agent_jobs.json()['Refs']:
            resources.append({'name': job['Name'], 'id': job['UID']})
        return resources

    def get_vcenters(self):
        from resourcehandlers.vmware.models import VsphereResourceHandler
        if self.ip_or_names:
            return VsphereResourceHandler.objects.filter(ip__in=self.ip_or_names)
        vcenters_response = self.api_get("/api/managedServers?format=Entity")
        for ms in vcenters_response.json()['ManagedServers']:
            if ms['ManagedServerType'] == 'VC':
                self.ip_or_names.append(ms['Name'])

        return VsphereResourceHandler.objects.filter(ip__in=self.ip_or_names)

    def install_agent(self, template, context):
        result = self.execute_script(template, context)
        return result

    def refresh_server(self, server, context=None):

        result = self.execute_script(CHECK_VM, context)
        if result:
            output = result.split('\n')
            veeam_agent_id = \
                [x.split(':')[-1].strip()
                 for x in output if x.split(':')[0].strip() == 'Id'][-1]
            server.veeam_agent_id = veeam_agent_id

        else:
            server.veeam_agent_id = None

        server.save()
        return server

    def take_backup(self, template, context):
        output = self.execute_script(template, context)
        output = output.split('\n')

        try:
            result = [x.split(':')[-1].strip()
                      for x in output if x.split(':')[0].strip() == 'Result'][-1]
        except Exception as e:
            logger.info(f"Error occurred while trying to parse result: {e}")
            logger.info(f"The output is {output}")
            result = ''
        return result

    def restore_backup_to_cloud(self, template, context):
        result = self.execute_script(template, context)
        return result

    def execute_script(self, template, context):
        ci = self.get_connection_info()
        template = generate_string_from_template(template=template,
                                                 group=None, env=None,
                                                 os_build=None, context=context)
        ci.protocol = "winrm"
        result = ci.execute_script(script_contents=template)
        return result

    def should_install_agent(self, server):
        # If the Server has a veeam_agent, no agent install is required
        if server.veeam_agent_id:
            return False
        else:
            # Refresh the server and check if it has agent installed.
            server = self.refresh_server(server=server, context={
                                         'veeam_server': self.connection_info, 'server': server})
            if server.veeam_agent_id:
                return False
            else:
                return True

    def get_backups(self):
        if self.backup_resources:
            return self.backup_resources
        if not self.connection_info:
            return []
        backups = self.api_get("/api/backups")

        for backup in backups.json()['Refs']:
            self.backup_resources.append({'name': backup['Name'], 'id': backup['UID']})
        return self.backup_resources

    def get_restore_points(self, hostname):
        if self.discovered_vm_restore_points:
            return self.discovered_vm_restore_points

        if not self.connection_info:
            return None

        vm_restore_points = self.api_get("/api/vmRestorePoints")

        for vm_restore_point in vm_restore_points.json()['Refs']:
            href = vm_restore_point['Links'][3]['Href']
            header = {"X-RestSvcSessionId": self.session_id,
                      "Accept": "Application/json"}
            response = requests.get(url=href, headers=header)
            restore_href = response.json()['Links'][0]['Href']
            restore_href = restore_href.split('/')[-1]
            name = vm_restore_point['Name']
            time = name.split('@')[-1]
            if name.startswith(hostname):
                self.discovered_vm_restore_points.append({
                    'Name': name,
                    'time': time,
                    'Id': vm_restore_point['UID'],
                    'Href': vm_restore_point['Href'],
                    'restore_point_href': restore_href
                })
        return self.discovered_vm_restore_points

    def create_custom_fields_as_needed(self):
        from c2_wrapper import create_custom_field

        cf_dict = dict(
            name='veeam_agent_id',
            type='STR',
            label='Veeam Agent ID',
            description='Veeam Agent ID that has been istalled',
            show_as_attribute=True
        )
        create_custom_field(**cf_dict)

    def get_summary(self):
        if self.backup_servers and self.total_jobs and self.total_backups and self.agent_jobs:
            return {'backup_servers': len(self.backup_servers),
                    'total_jobs': len(self.total_jobs) + len(self.agent_jobs),
                    'total_backups': len(self.total_backups)}

        if not self.connection_info:
            return None
        url_backup_servers = self.connection_info.format_url(
            auth=False) + "/api/backupServers"
        header = {'X-RestSvcSessionId': self.session_id,
                  'Accept': "Application/json"}
        backup_servers = requests.get(url=url_backup_servers, headers=header, verify=self.verify_ssl_checks)
        url_jobs = self.connection_info.format_url(auth=False) + "/api/jobs"
        jobs = requests.get(url=url_jobs, headers=header, verify=self.verify_ssl_checks)
        url_backups = self.connection_info.format_url(
            auth=False) + "/api/backups"
        backups = requests.get(url=url_backups, headers=header, verify=self.verify_ssl_checks)
        url_agent_jobs = self.connection_info.format_url(
            auth=False) + "/api/agents/jobs"
        agent_jobs = requests.get(url=url_agent_jobs, headers=header, verify=self.verify_ssl_checks)
        self.backup_servers = backup_servers.json()['Refs']
        self.total_jobs = jobs.json()['Refs']
        self.total_backups = backups.json()['Refs']
        self.agent_jobs = agent_jobs.json()['Refs']
        return {'backup_servers': len(self.backup_servers),
                'total_jobs': len(self.total_jobs) + len(self.agent_jobs),
                'total_backups': len(self.total_backups)}

    def get_veeam_server_session_id(self):
        ci = self.get_connection_info()
        url = "http://{host_name}:9399/api/sessionMngr/?v=v1_4".format(
            host_name=ci.ip)
        encoded_credentials = base64.b64encode(
            (ci.username + ':' + ci.password).encode())
        headers = {
            "Authorization":
                "Basic {credentials}".format(
                    credentials=encoded_credentials.decode())
        }
        response = requests.post(url, headers=headers)
        rest_svc_session_id = response.headers.get('X-RestSvcSessionId')
        return rest_svc_session_id

    def setup_veeam_install_agent_action(self):
        veeam_agent_hook = {
            'name': "Install Veeam Agent",
            'description': "Installs Veeam agent on Server",
            'hook_point': None,
            'module': '/var/opt/cloudbolt/proserv/xui/veeam/install_agent.py'
        }
        create_hook(**veeam_agent_hook)

    def setup_take_backup_action(self):
        veeam_backup_hook = {
            'name': "Take Veeam Backup",
            'description': "Takes backup of this server.",
            'hook_point': None,
            'module': '/var/opt/cloudbolt/proserv/xui/veeam/take_backup.py',
        }
        create_hook(**veeam_backup_hook)

    def setup_restore_backup_action(self):
        veeam_restore_backup_hook = {
            'name': "Restore Veeam Backup",
            'description': "Restores a server backup",
            'hook_point': None,
            'module': '/var/opt/cloudbolt/proserv/xui/veeam/restore_backup.py',
        }
        create_hook(**veeam_restore_backup_hook)

    def setup_restore_backup_to_ec2__action(self):
        veeam_restore_backup_to_ec2_hook = {
            'name': "Restore Veeam Backup To EC2",
            'description': "Restores a server backup to ec2",
            'hook_point': None,
            'module': '/var/opt/cloudbolt/proserv/xui/veeam/restore_backup_to_ec2.py',
        }
        create_hook(**veeam_restore_backup_to_ec2_hook)

    def setup_restore_backup_to_azure_action(self):
        veeam_restore_backup_hook = {
            'name': "Restore Veeam Backup To Azure",
            'description': "Restores a server backup",
            'hook_point': None,
            'module': '/var/opt/cloudbolt/proserv/xui/veeam/restore_backup_to_azure.py',
        }
        create_hook(**veeam_restore_backup_hook)
