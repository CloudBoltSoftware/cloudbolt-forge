"""
This is a working sample CloudBolt inbound web hook plug-in for you to start with.

These method runs synchronously. i.e. no job is created and the HTTP call will not return until
the method returns. The HTTP response will contain the dictionary which is returned from the method.

See the "CloudBolt Plug-ins" section of the docs for more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
from common.methods import set_progress
import json

from infrastructure.models import Server

# Set the Server ID in CloudBolt where you want to execute the PowerShell script
SERVER_ID = 23416

def inbound_web_hook_post(*args, parameters={}, **kwargs):
    """
    Use this method for operations that make any kind of change. Remove
    this method entirely if your inbound web hook is read only.
    """

    set_progress(f"This message will show up in CloudBolt's application.log. args: {args}, kwargs: {kwargs}, parameters: {parameters}")
    script = powershell_script(json.dumps(parameters))
    server = Server.objects.get(id=SERVER_ID)
    result = server.execute_script(script_contents=script)
    return(
        {
            "message": "Successfully executed the PowerShell Script",
            "result": result
        }
    )


def powershell_script(parameters):
    script = f"$parameters = ConvertFrom-Json '{parameters}'\n"
    script += """
    Write-Output "This is a PowerShell script that will be run by the inbound web hook"
    Write-Output "The parameters passed in were:"
    Write-Output $parameters
    
    Write-Output "My Variable: " $parameters.my_var
    
    Write-Output "My Variable: " $parameters.hostname
    
    """
    return script