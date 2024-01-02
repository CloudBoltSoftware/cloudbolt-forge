"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
from common.methods import set_progress
from shared_modules.generated_options import generate_options_for_environment as env_options


def generate_options_for_environment(field=None, **kwargs):
    return env_options(field, "Amazon Web Services", **kwargs)
    

def run(job, *args, **kwargs):
    env_id = "{{environment}}"
    set_progress(f"env_id: {env_id}")