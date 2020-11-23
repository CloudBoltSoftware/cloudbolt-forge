import dateutil.parser
from dateutil import tz
from datetime import timedelta
import time

import requests
from requests.auth import HTTPBasicAuth

from xui.solar_winds.solar_winds_scripts import TEST_SERVER_CONNECTION
from common.methods import generate_string_from_template
from utilities.models import ConnectionInfo
from c2_wrapper import create_hook


class SolarWindsManager:
    def __init__(self):
        self.ci_for_server = ConnectionInfo.objects.filter(name__iexact='SolarWinds Connection Info').first()
        self.ci_for_rest = ConnectionInfo.objects.filter(name__iexact='SolarWinds Connection Info Rest').first()

    def get_connection_info(self, for_server=False):
        if for_server:
            return self.ci_for_server
        return self.ci_for_rest

    def execute_script(self, template, context):
        ci = self.get_connection_info(for_server=True)
        template = generate_string_from_template(template=template,
                                                 group=None, env=None,
                                                 os_build=None, context=context)
        ci.protocol = "winrm"
        result = ci.execute_script(script_contents=template)
        return result

    def install_windows_agent(self, template, context):
        result = self.execute_script(template, context)
        return result

    def install_linux_agent(self, server, template, context):
        linux_template = generate_string_from_template(template=template,
                                                       group=None, env=None,
                                                       os_build=None, context=context)

        result = server.execute_script(script_contents=linux_template, run_with_sudo=True)
        return result

    def verify_rest_credentials(self, **kwargs):
        if 'connection_info' in kwargs:
            ci = kwargs.get('connection_info')
        else:
            ci = self.ci_for_rest
        ip = ci.ip
        port = ci.port
        protocol = ci.protocol
        username = ci.username
        password = ci.password

        path = "/SolarWinds/InformationService/v3/Json/Query?query=SELECT+TOP+10+AccountID+FROM+Orion.Accounts"
        url = f"{protocol}://{str(ip)}:{port}{path}"

        try:
            response = requests.get(url, auth=HTTPBasicAuth(
                    username, password), verify=False)
        except Exception:
            return False
        return response.ok

    def verify_server_connection(self, **kwargs):
        if 'server_connection_info' in kwargs:
            ci = kwargs.get('server_connection_info')
        else:
            ci = self.ci_for_server

        template = generate_string_from_template(template=TEST_SERVER_CONNECTION,
                                                 group=None, env=None,
                                                 os_build=None, context={})

        try:
            ci.protocol = "winrm"
            result = ci.execute_script(script_contents=template)
            if result.split('\r\n'):
                return (True, "Connection succesful")
            else:
                return False, "Could not connect to the server"
        except Exception as error:
            return False, error

    def get_solar_winds_rest_ci(self):
        return self.ci_for_rest

    def get_solar_winds_server_ci(self):
        return self.ci_for_server

    def get_solar_winds_nodes(self):
        ci = self.ci_for_rest
        path = "/SolarWinds/InformationService/v3/Json/Query?query=SELECT+TOP+1000+NodeID,IPAddress,NodeName,Vendor+FROM+Orion.Nodes"
        try:
            url = f"{ci.protocol}://{str(ci.ip)}:{ci.port}{path}"
            response = requests.get(url, auth=HTTPBasicAuth(
                ci.username, ci.password), verify=False)
            return response.json().get('results')
        except Exception:
            return []
    def generate_url(self, path):
        ci = self.get_connection_info()
        url = ci.format_url() + f'/{path}'
        return url

    def get_auth(self):
        # returns a HTTPBasicAuth object that has been authenticated
        ci = self.get_connection_info()
        return HTTPBasicAuth(ci.username, ci.password)

    def is_agent_installed(self, server_ip):
        response = self.send_get_requests(url='SolarWinds/InformationService/v3/Json/Query?query=SELECT+IpAddress+FROM+Orion.Nodes')
        if response.ok:
            ip_addresses = response.json().get('results')
            exists = [address['IpAddress'] for address in ip_addresses if address['IpAddress'] == server_ip]
            if not exists:
                # Ip not found thus agent not installed
                return False, 'Not Installed'
            else:
                return True, 'Installed'

        return False, response.reason

    def get_node_id(self, server_ip):
        response = self.send_get_requests('SolarWinds/InformationService/v3/Json/Query?query=SELECT+IpAddress,NodeId+FROM+Orion.Nodes')
        if response.ok:
            nodes_ip_addresses = response.json().get('results')
            node_id = [nodes_ip_address['NodeId'] for nodes_ip_address in nodes_ip_addresses if nodes_ip_address['IpAddress'] == server_ip]
            if node_id:
                return node_id[0]

    def get_server_stat(self, server_ip):
        node_id = self.get_node_id(server_ip)
        if node_id:
            response = self.send_get_requests(f'SolarWinds/InformationService/v3/Json/Query?query=SELECT+NodeId,CpuCount,TotalMemory, CpuLoad, MemoryUsed+FROM+Orion.NodesStats+WHERE+NodeID={node_id}')
            if response.ok:
                server_stats = response.json().get('results')[0]
                return True, server_stats

            return False, response.reason
        else:
            return False, 'Server not registered on the solarwinds server.'

    def get_cpu_load_metrics(self, server_ip):
        node_id = self.get_node_id(server_ip)
        response = self.send_get_requests(f'SolarWinds/InformationService/v3/Json/Query?query=SELECT+NodeId,DateTime,MinLoad,MaxLoad,AvgLoad+FROM+Orion.CPULoad+WHERE+NodeID={node_id}')
        if response.ok:
            results = response.json().get('results')
            data = [[self.convert_time_to_timestamp(load.get('DateTime')), load.get('AvgLoad')] for load in results]
            return data

    def get_memory_used_metrics(self, server_ip):
        node_id = self.get_node_id(server_ip)
        response = self.send_get_requests(f'SolarWinds/InformationService/v3/Json/Query?query=SELECT+NodeId,DateTime,AvgPercentMemoryUsed+FROM+Orion.CPULoad+WHERE+NodeID={node_id}')
        if response.ok:
            results = response.json().get('results')
            data = [[self.convert_time_to_timestamp(load.get('DateTime')), load.get('AvgPercentMemoryUsed')] for load in results]
            return data

    def get_network_latency_metrics(self, server_ip):
        node_id = self.get_node_id(server_ip)
        response = self.send_get_requests(f'SolarWinds/InformationService/v3/Json/Query?query=SELECT+NodeId,DateTime,AvgResponseTime+FROM+Orion.ResponseTime+WHERE+NodeID={node_id}')
        if response.ok:
            results = response.json().get('results')
            data = [[self.convert_time_to_timestamp(load.get('DateTime')), load.get('AvgResponseTime')] for load in results]
            return data

    def send_get_requests(self, url):
        url = self.generate_url(url)
        response = requests.get(url, auth=self.get_auth(), verify=False)
        return response

    def convert_time_to_timestamp(self, date):
        date_time = dateutil.parser.parse(date)
        # Time displayed on the Graph is 1 hour behind UTC
        utc_zone = tz.tzutc()
        utc_time = date_time.astimezone(utc_zone)
        utc_time = utc_time - timedelta(hours=1)

        return utc_time.timestamp()*1000

    def setup_solar_winds_install_agent_action(self):
        solar_winds_hook = {
            'name': "Install SolarWinds Agent",
            'description': "Installs SolarWinds Agent on a Server",
            'hook_point': None,
            'module': '/var/opt/cloudbolt/proserv/xui/solar_winds/install_agent.py',
        }
        create_hook(**solar_winds_hook)

    def is_license_valid(self):
        response = self.send_get_requests(f'SolarWinds/InformationService/v3/Json/Query?query=SELECT+LicenseExpiresOn+FROM+Orion.Licensing.Licenses')
        if response.ok:
            results = response.json().get('results')
            for license in results:
                if float(self.convert_time_to_timestamp(license.get('LicenseExpiresOn')) > (time.time()* 1000)):
                    return True

            return False
        raise Exception(response.reason)
