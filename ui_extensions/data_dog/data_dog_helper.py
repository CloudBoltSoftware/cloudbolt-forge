import ast

import requests

from utilities.models import ConnectionInfo
from common.methods import generate_string_from_template
from c2_wrapper import create_hook


class DataDog(object):
    def __init__(self):
        ci = ConnectionInfo.objects.filter(
            name__iexact='Datadog Connection Credentials').first()
        self.connection_info = ci

    def get_connection_info(self):
        return self.connection_info

    def verify_connection(self, connection_info=None):
        if connection_info:
            self.connection_info = connection_info
        api_key = self.get_api_key()
        if not api_key:
            return False, 'No API Key Found'
        url = self.generate_url("validate")
        url += f"?api_key={api_key}"

        response = requests.get(url)
        return response.ok, response.reason

    def get_api_key(self):
        return ast.literal_eval(self.connection_info.headers).get('api_key')

    def get_app_key(self):
        return ast.literal_eval(self.connection_info.headers).get('app_key')

    def generate_url(self, path):
        connection_info = self.get_connection_info()

        url = connection_info.protocol + "://" + connection_info.ip + f"{path}"

        return url

    def download_agent(self, template, context, server):
        # First download the agent file.
        # Checking if the file already exists would also be a good thing.
        download_file_result = self.execute_script(template, context, server)
        return download_file_result

    def install_agent(self, template, context, server, run_with_sudo):
        install_agent_result = self.execute_script(template, context, server, run_with_sudo)
        return install_agent_result

    def uninstall_agent(self, server):
        try:
            if server.use_tech_specific_script_execution():
                server.tech_specific_script_execution = False
            if server.os_family and server.os_family.get_base_name() == 'Linux':
                if server.os_family.name.lower == 'red hat':
                    try:
                        result = server.execute_script(
                            script_contents='sudo yum remove datadog-agent -y',
                            run_with_sudo=True)
                        return True, result
                    except Exception as error:
                        return False, error

                else:
                    try:
                        result = server.execute_script(
                            script_contents='sudo apt-get --purge remove datadog-agent -y',
                            run_with_sudo=True)
                        return True, result
                    except Exception as error:
                        return True, error

            if server.is_windows():
                try:
                    script_contents = "(Get-WmiObject -Class Win32_Product -Filter \"Name='Datadog Agent'\" -ComputerName . ).Uninstall()"
                    result = server.execute_script(script_contents=script_contents)
                    return True, result
                except Exception as error:
                    return False, error

        except Exception as error:
            return False, error

    def check_agent_status(self, template, context, server):
        agent_status_result = self.execute_script(template, context, server)
        return agent_status_result

    def execute_script(self, template, context, server, run_with_sudo=False):
        template = generate_string_from_template(template=template,
                                                 group=None, env=None,
                                                 os_build=None, context=context)

        result = server.execute_script(script_contents=template, run_with_sudo=run_with_sudo)
        return result

    def setup_data_dog_install_agent_action(self):
        solar_winds_hook = {
            'name': "Install DataDog Agent",
            'description': "Installs DataDog Agent on a Server",
            'hook_point': None,
            'module': '/var/opt/cloudbolt/proserv/xui/data_dog/install_agent.py',
        }
        create_hook(**solar_winds_hook)

    def setup_data_dog_uninstall_agent_action(self):
        solar_winds_hook = {
            'name': "UnInstall Datadog Agent",
            'description': "UnInstalls Datadog Agent on a Server",
            'hook_point': None,
            'module': '/var/opt/cloudbolt/proserv/xui/data_dog/uninstall_agent.py',
        }
        create_hook(**solar_winds_hook)
