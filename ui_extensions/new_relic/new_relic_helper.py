import requests
import ast

from utilities.models import ConnectionInfo
from common.methods import generate_string_from_template
from c2_wrapper import create_hook


class NewRelicManager:
    def __init__(self):
        self.connection_info = ConnectionInfo.objects.filter(name__iexact='New Relic Connection Info').first()

    def get_connection_info(self):
        return self.connection_info

    def get_query_key(self, connection_info=None):
        if connection_info:
            headers = ast.literal_eval(connection_info.headers)
        else:
            headers = ast.literal_eval(self.get_connection_info().headers)

        return headers.get('query_key')

    def get_license_key(self, connection_info=None):
        if connection_info:
            headers = ast.literal_eval(connection_info.headers)
        else:
            headers = ast.literal_eval(self.get_connection_info().headers)
        return headers.get('license_key')

    def get_new_relic_account_id(self, connection_info=None):
        if connection_info:
            headers = ast.literal_eval(connection_info.headers)
        else:
            headers = ast.literal_eval(self.get_connection_info().headers)
        return headers.get('new_relic_account_id')

    def verify_credentials(self, proto=None, ip=None, port=None, headers=None):
        if port and int(port) not in [80, 443]:
            return False, "Valid ports are 80 for HTTP and 443 for HTTPS"
        if (proto =='http' and port != 80) or (proto =='https' and port != 443):
            return False, "HTTP uses port 80 while HTTPS uses port 443"

        if ip and port and headers:
            ci = ConnectionInfo(name="test", protocol=proto, port=port, ip=ip, headers=headers)
        else:
            ci = self.get_connection_info()

        query_key = self.get_query_key(ci)
        license_key = self.get_license_key(ci)
        new_relic_account_id = self.get_new_relic_account_id(ci)

        if query_key is None:
            return False, "query_key must be set"

        if license_key is None:
            return False, "license_key must be set"

        if new_relic_account_id is None:
            return False, "new_relic_account_id must be set"

        url = ci.format_url() + f'/v1/accounts/{new_relic_account_id}/query?nrql=SELECT%20uniques(hostname)%20FROM%20SystemSample'

        headers = {
            'X-Query-Key': query_key
        }
        try:
            response = requests.get(url, headers=headers)
        except Exception as error:
            return False, error

        return response.ok, response.reason

    def is_agent_installed(self, server):
        ci = self.get_connection_info()
        # url = "https://insights-api.newrelic.com:443/v1/accounts/2426245/query?nrql=SELECT%20uniques(hostname)%20FROM%20SystemSample"
        headers = {
            'X-Query-Key': self.get_query_key()
        }
        url = ci.format_url() + f'/v1/accounts/{self.get_new_relic_account_id()}/query?nrql=SELECT%20uniques(hostname)%20FROM%20SystemSample'
        response = requests.get(url, headers=headers)
        if response.ok:
            servers = response.json().get('results')[0].get('members')
            # For linux hosts, the hostname from new relic
            # corresponds to hostname returned by the hostname command on the server
            if not server.is_windows():
                hostname = server.execute_script(script_contents='hostname').strip('\r\n')
                return hostname in servers
            return server.hostname[:15] in servers
        return False

    def download_windows_agent(self, template, context, server):
        # First download the agent file.
        download_file_result = self.execute_script(template, context, server)
        return download_file_result

    def install_agent_on_windows(self, template, context, server):
        # Installs the New Relic agent on windows machine
        install_result = self.execute_script(template, context, server)
        return install_result

    def install_agent_on_linux(self, template, context, server):
        # All commands needs to be executed as sudo
        if server.use_tech_specific_script_execution():
            server.tech_specific_script_execution = False

        template = generate_string_from_template(template=template,
                                                 group=None, env=None,
                                                 os_build=None, context=context)

        install_result = server.execute_script(script_contents=template, run_with_sudo=True)
        return install_result

    def uninstall_agent(self, server):
        try:
            if server.use_tech_specific_script_execution():
                server.tech_specific_script_execution = False
            if server.os_family and server.os_family.get_base_name() == 'Linux':
                if server.is_ubuntu():
                    result = server.execute_script(script_contents='sudo rm /etc/newrelic-infra.yml && sudo apt-get remove newrelic-infra -y', run_with_sudo=True)
                    return True, result
                else:
                    result = server.execute_script(script_contents='sudo rm /etc/newrelic-infra.yml && sudo yum remove newrelic-infra -y', run_with_sudo=True)
                    return True, result

            if server.is_windows():
                try:
                    server.execute_script(script_contents='net stop newrelic-infra')
                except Exception:
                    pass
                script_contents = r"Remove-Item -Recurse -Force 'C:\Program Files\New Relic'"
                result = server.execute_script(script_contents=script_contents)
                return True, result

        except Exception as error:
            return False, error

    def execute_script(self, template, context, server):
        template = generate_string_from_template(template=template,
                                                 group=None, env=None,
                                                 os_build=None, context=context)

        result = server.execute_script(script_contents=template)
        return result

    def get_server_statistics(self, server):
        headers = {
            'X-Query-Key': self.get_query_key()
        }
        url = self.get_connection_info().format_url() + f'/v1/accounts/{self.get_new_relic_account_id()}/query?nrql=SELECT%20*%20FROM%20SystemSample'
        response = requests.get(url, headers=headers)
        if response.ok:
            servers_events = response.json().get('results')[0].get('events')
            # For windows, New Relic truncates servername to 15 characters
            hostname = server.hostname[:15]
            if not server.is_windows():
                hostname = server.execute_script(script_contents='hostname').strip('\r\n')

            current_server_events = [event for event in servers_events if event.get('hostname') == hostname]
            return current_server_events
        return []

    def setup_new_relic_install_agent_action(self):
        new_relic_hook = {
            'name': "Install New Relic Agent",
            'description': "Installs New Relic Agent on a Server",
            'hook_point': None,
            'module': '/var/opt/cloudbolt/proserv/xui/new_relic/install_agent.py',
        }
        create_hook(**new_relic_hook)

    def setup_new_relic_uninstall_agent_action(self):
        new_relic_hook = {
            'name': "UnInstall New Relic Agent",
            'description': "UnInstalls New Relic Agent on a Server",
            'hook_point': None,
            'module': '/var/opt/cloudbolt/proserv/xui/new_relic/uninstall_agent.py',
        }
        create_hook(**new_relic_hook)
