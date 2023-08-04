"""
This module is used to store the methods for setting up a CloudBolt XUI. This
could be reused for other XUIs. with minimal changes needed. The following
directories are supported:
- blueprints - Any blueprints must be exported from API v2 and placed in a
  /blueprints/ directory in an extracted format. The directory structure must
  be the same as the export.
- inbound_webhooks - Any inbound webhooks must be exported from API v3 and
  placed an /inbound_webhooks/ directory in an extracted format. The directory
  structure must be the same as the export.
- parameters - One or more json files can be placed in the /parameters/
  directory - each json file should contain a single param or a list of params.
  See the docstring for configure_params for more details.
- recurring_jobs - Any recurring jobs must be exported from API v3 and placed
  in a /recurring_jobs/ directory in an extracted format. The directory
  structure must be the same as the export.

XUI Requirements:
- In __init__.py you must have at least the following three lines. Replace
  <xui_name> with the name of your XUI.
    from xui.<xui_name>.config import run_config
    __version__ = "1.0"
    run_config(__version__)
- With every release of the XUI, the __version__ variable must be updated.
"""
import json
import os
from os import path
from packaging import version
from django.utils.text import slugify
from c2_wrapper import create_custom_field
from cbhooks.api.v3.serializers import BaseActionSerializer
from cbhooks.models import CloudBoltHook, InboundWebHook, RecurringActionJob
from externalcontent.models import OSFamily
from jobs.models import RecurringJob
from resourcehandlers.models import ResourceTechnology
from servicecatalog.models import ServiceBlueprint
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

XUI_PATH = path.dirname(path.abspath(__file__))
XUI_NAME = XUI_PATH.split("/")[-1]
CONFIG_FILE = f'/var/opt/cloudbolt/proserv/xui/xui_versions.json'
BASE_NAME = __package__.split(".")[-1]
SETTINGS_FILE = __file__
TEMPLATE_DIR = f"{BASE_NAME}/templates"
STATIC_DIR = f"{BASE_NAME}/static"
TMP_PATH = "/var/tmp/"


def get_data_from_config_file(property_key):
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        data = config[XUI_NAME][property_key]
    return data


# If we find a Blueprint with the same name, should it be overwritten? Since
# Remote source for blueprints is still set to use API V2, we can't use the
# Global ID to check if the blueprint is the same. We can only check the name.
try:
    OVERWRITE_EXISTING_BLUEPRINTS = True
        # get_data_from_config_file('OVERWRITE_EXISTING_BLUEPRINTS')
except Exception:
    OVERWRITE_EXISTING_BLUEPRINTS = False
# From what I can tell, when a Blueprint is using a remote source, the actions
# are only updated at initial creation. Setting this toggle to True would
# set each action to use the remote source - forcing update of the actions when
# the XUI gets updated
try:
    SET_ACTIONS_TO_REMOTE_SOURCE = get_data_from_config_file(
        'SET_ACTIONS_TO_REMOTE_SOURCE')
except Exception:
    SET_ACTIONS_TO_REMOTE_SOURCE = True


def run_config(xui_version):
    config_needed = False
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            current_version = config[XUI_NAME]["current_version"]
            if version.parse(current_version) < version.parse(xui_version):
                logger.info(f"Current Version: {current_version} is less than"
                            f" {xui_version}. Running config.")
                config_needed = True
    except (FileNotFoundError, KeyError):
        logger.info(f"Config file or key not found going to run configuration")
        config_needed = True
    if config_needed:
        logger.info("Running Configuration")
        configure_xui()
        try:
            config
        except NameError:
            config = {}
        config[XUI_NAME] = {
            "current_version": xui_version,
            "SET_ACTIONS_TO_REMOTE_SOURCE": SET_ACTIONS_TO_REMOTE_SOURCE,
            "OVERWRITE_EXISTING_BLUEPRINTS": OVERWRITE_EXISTING_BLUEPRINTS
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)


def configure_xui():
    configure_cloudbolt_hooks()


def configure_cloudbolt_hooks():
    cbh_dir = f'{XUI_PATH}/cloudbolt_hooks/'
    try:
        cbhs = os.listdir(cbh_dir)
    except FileNotFoundError:
        logger.info(f"No CloudBolt Hooks directory found at {cbh_dir}")
        return
    for cbh in cbhs:
        logger.info(f"Starting import of Inbound Webhook: {cbh}")
        hook_json_path = f'{cbh_dir}{cbh}/{cbh}.json'
        with open(hook_json_path, 'r') as f:
            hook_json = json.load(f)
        hook = create_cloudbolt_hook(hook_json, cbh_dir, cbh)


def create_cloudbolt_hook(hook_config, cbh_dir, cbh):
    serializer = BaseActionSerializer()
    serializer.replace_existing = True
    script_filename = hook_config["script_filename"]
    hook_py_path = f'{cbh_dir}{cbh}/{script_filename}'
    tmp_hook_py_path = f'{TMP_PATH}{script_filename}'
    # copy the hook file to a temp location so CloudBolt can upload
    os.system(f'cp {hook_py_path} {tmp_hook_py_path}')
    file_map = {script_filename: tmp_hook_py_path}
    hook = serializer.create_resource_from_metadata(hook_config, file_map)
    hook.global_id = hook_config["id"]
    hook.save()
    if SET_ACTIONS_TO_REMOTE_SOURCE:
        hook.source_code_url = f'file://{hook_py_path}'
        hook.save()
        hook.fetch_remote_content()
        logger.info(f"Finished refreshing: {hook.name} from remote source")

    return hook
