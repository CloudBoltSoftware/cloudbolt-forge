"""
Config Module can be used to load initial configuration for a CloudBolt XUI.

If desired, you can change the CONFIG_FILE variable to point to a different
location. The default location is:
    /var/opt/cloudbolt/proserv/xui/xui_versions.json

If the file does not exist, it will be created. The file will be in the
following format:
{
    "xui_name": {
        "current_version": "0.0.0",
        "SET_ACTIONS_TO_REMOTE_SOURCE": True,
        "OVERWRITE_EXISTING_BLUEPRINTS": True
    }
}

The current_version will be updated to the version of the XUI that is being
installed. The other two variables are used to determine if the actions should
be set to remote source and if existing blueprints should be overwritten.

The config module will look for the following directories in the XUI directory
and import the content from them:
    blueprints
    server_actions
    recurring_jobs
    inbound_webhooks
    orchestration_hooks

To prepare CloudBolt content to use this method:
1. Create a directory in the XUI directory for each type of content you want to
    import. For example, if you want to import blueprints, create a directory
    called blueprints.
2. Export a Blueprint from CloudBolt - this will be in zip format
3. Transfer the zip file to the directory you created in step 1
4. Unzip the file (and any zipped subdirectories) into the directory you
    created in step 1
5. Repeat steps 2-4 for each piece of content you want to import
6. Ensure that the __init__.py file in the XUI directory has the following
    lines:
        from .config import run_config
        __version__ = "1.0" # Or whatever version you want to use
        run_config(__version__)
7. Restart Apache on the server, then refresh the XUI in CloudBolt, the content
    should be imported automatically. TO follow the logs after the restart to
    ensure the import is successful, run the following command:
    > tail -f /var/log/cloudbolt/application.log
8. If the content isn't showing up, the best way to troubleshoot import failures
    is to run shell plus, any errors will be displayed in the console:
    > /opt/cloudbolt/manage.py shell_plus
"""
import json
import os
from os import path
from packaging import version

from cbhooks.models import CloudBoltHook, RecurringActionJob, InboundWebHook, \
    ServerAction, HookPointAction, HookPoint
from externalcontent.models import OSFamily
from servicecatalog.models import ServiceBlueprint
from resourcehandlers.models import ResourceHandler, ResourceTechnology
from django.utils.text import slugify
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

XUI_PATH = path.dirname(path.abspath(__file__))
XUI_NAME = XUI_PATH.split("/")[-1]
CONFIG_FILE = f'/var/opt/cloudbolt/proserv/xui/xui_versions.json'


def get_data_from_config_file(property_key):
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        data = config[XUI_NAME][property_key]
    return data


# If we find a Blueprint with the same name, should it be overwritten?
OVERWRITE_EXISTING_BLUEPRINTS = True
try:
    get_data_from_config_file('OVERWRITE_EXISTING_BLUEPRINTS')
except Exception:
    logger.debug("OVERWRITE_EXISTING_BLUEPRINTS not found in config file. "
                 "Defaulting to False")
# Setting this toggle to True would set each action to use the remote source -
# forcing update of the actions when the XUI gets updated
SET_ACTIONS_TO_REMOTE_SOURCE = True
try:
    get_data_from_config_file('SET_ACTIONS_TO_REMOTE_SOURCE')
except Exception:
    logger.debug("SET_ACTIONS_TO_REMOTE_SOURCE not found in config file. "
                 "Defaulting to True")


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
    except Exception:
        logger.info(f"Config file not found going to run configuration")
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
    configure_blueprints()
    configure_server_actions()
    configure_recurring_jobs()
    configure_inbound_webhooks()
    configure_orchestration_hooks()


def configure_blueprints():
    blueprints_dir = f'{XUI_PATH}/blueprints/'
    for bp in os.listdir(blueprints_dir):
        bp_dir = f'{blueprints_dir}{bp}/'
        bp_path = f'{bp_dir}{bp}.json'
        with open(bp_path, 'r') as f:
            bp_json = json.load(f)
        bp_name = bp_json["name"]
        try:
            bp_global_id = bp_json["id"]
        except KeyError:
            logger.warning(f"Blueprint: {bp_name} does not have an id. "
                           f"Skipping")
            continue

        bp, created = ServiceBlueprint.objects.get_or_create(
            global_id=bp_global_id,
            status='ACTIVE'
        )
        if not created:
            if OVERWRITE_EXISTING_BLUEPRINTS:
                logger.info(f"Overwriting Blueprint: {bp_name}")
            else:
                logger.info(f"Blueprint: {bp_name} already exists. Skipping")
                continue
        bp.remote_source_url = f'file://{bp_path}'
        bp.save()
        bp.refresh_from_remote_source()
        logger.info(f"Finished refreshing: {bp_name} from remote source")
        set_actions_to_remote_source(bp_dir, bp_json, created)


def set_actions_to_remote_source(bp_dir, bp_json, created):
    if SET_ACTIONS_TO_REMOTE_SOURCE or created:
        logger.info(f'Starting to set actions to remote source for BP: '
                    f'{bp_json["name"]}')
        action_datas = []  # Tuples of (action_name, action_path)
        elements = ["teardown_items", "deployment_items", "management_actions",
                    'discovery_plugin']
        for element in elements:
            if element == 'discovery_plugin':
                actions = [bp_json[element]]
            else:
                actions = bp_json[element]
            for action in actions:
                action_data = get_action_data(action, bp_dir, element)
                action_datas.append(action_data)
        for action_data in action_datas:
            action_name, action_path = action_data
            logger.info(f"Setting action: {action_name} to remote source")
            set_action_to_remote_source(action_name, action_path)
    else:
        logger.info("Not setting actions to remote source. Update the "
                    "SET_ACTIONS_TO_REMOTE_SOURCE variable to True if you "
                    "want to do this")
    return None


def set_action_to_remote_source(action_name, action_path):
    try:
        action = CloudBoltHook.objects.get(name=action_name)
        action.source_code_url = f'file://{action_path}'
        action.save()
    except:
        logger.warning(f"Could not find action: {action_name}, will not be "
                       f"able to set to remote source")


def get_action_data(action, bp_dir, item_name):
    if item_name == 'management_actions':
        file_name = slugify(action["label"]).replace("-", "_")
        json_file = f'{file_name}.json'
        json_path = f'{bp_dir}{file_name}/{file_name}/{json_file}'
        action_name = action["label"]
    elif item_name == 'discovery_plugin':
        file_name = slugify(action["title"]).replace("-", "_")
        json_file = f'{file_name}.json'
        json_path = f'{bp_dir}{file_name}/{json_file}'
        action_name = action["title"]
    else:
        file_name = slugify(action["name"]).replace("-", "_")
        json_file = f'{file_name}.json'
        json_path = f'{bp_dir}{file_name}/{file_name}.json'
        action_name = action["name"]
    action_path = get_action_path_from_json(json_path, json_file)
    return action_name, action_path


def get_action_path_from_json(json_path, json_file):
    with open(json_path, 'r') as f:
        action_json = json.load(f)
    action_file = action_json["script_filename"]
    action_path = json_path.replace(json_file, action_file)
    return action_path


def configure_server_actions():
    server_actions_dir = f'{XUI_PATH}/server_actions/'
    try:
        server_actions = os.listdir(server_actions_dir)
    except FileNotFoundError:
        logger.info(f"No Server Actions directory found at "
                    f"{server_actions_dir}")
    for sa in server_actions:
        logger.info(f"Starting import of Server Action: {sa}")
        sa_file = f'{sa}.json'
        sa_path = f'{server_actions_dir}{sa}/{sa_file}'
        with open(sa_path, 'r') as f:
            sa_json = json.load(f)
        hook_name = sa_json["label"].replace(" ", "_").lower()
        hook_json_path = (f'{server_actions_dir}{sa}/{hook_name}/'
                          f'{hook_name}.json')
        with open(hook_json_path, 'r') as f:
            hook_json = json.load(f)
        script_filename = hook_json["script_filename"]
        hook_py_path = f'{server_actions_dir}{sa}/{hook_name}/{script_filename}'
        hook = create_cloudbolt_hook(hook_json, hook_py_path)
        create_server_action(sa_json, hook)


def create_server_action(sa_json, hook):
    global_id = sa_json["id"]

    defaults = {
        "label": sa_json["label"],
        "dangerous": sa_json["dangerous"],
        "dialog_message": sa_json["dialog_message"],
        "enabled": sa_json["enabled"],
        "extra_classes": sa_json["extra_classes"],
        "is_synchronous": sa_json["is_synchronous"],
        "maximum_version_required": sa_json["maximum_version_required"],
        "minimum_version_required": sa_json["minimum_version_required"],
        "new_tab_url": sa_json["new_tab_url"],
        "requires_approval": sa_json["requires_approval"],
        "sequence": sa_json["sequence"],
        "submit_button_label": sa_json["submit_button_label"],
        "hook": hook.orchestrationhook_ptr,
    }
    sa, created = ServerAction.objects.get_or_create(
        global_id=global_id,
        defaults=defaults)
    if not created:
        sa.hook = hook.orchestrationhook_ptr
        sa.save()
    return sa


def configure_recurring_jobs():
    recurring_jobs_dir = f'{XUI_PATH}/recurring_jobs/'
    try:
        recurring_jobs = os.listdir(recurring_jobs_dir)
    except FileNotFoundError:
        logger.info(f"No Recurring Jobs directory found at "
                    f"{recurring_jobs_dir}")
        return
    for rj in recurring_jobs:
        logger.info(f"Starting import of Recurring Job: {rj}")
        rj_file = f'{rj}.json'
        rj_path = f'{recurring_jobs_dir}{rj}/{rj_file}'
        with open(rj_path, 'r') as f:
            rj_json = json.load(f)
        hook_name = rj_json["name"].replace(" ", "_").lower()
        hook_json_path = f'{recurring_jobs_dir}{rj}/{hook_name}/{hook_name}.json'
        with open(hook_json_path, 'r') as f:
            hook_json = json.load(f)
        script_filename = hook_json["script_filename"]
        hook_py_path = f'{recurring_jobs_dir}{rj}/{hook_name}/{script_filename}'
        hook = create_cloudbolt_hook(hook_json, hook_py_path)
        create_recurring_job(rj_json, hook)


def create_recurring_job(rj_json, hook):
    global_id = rj_json["id"]

    defaults = {
        "name": rj_json["name"],
        "description": rj_json["description"],
        "schedule": rj_json["schedule"],
        "enabled": rj_json["enabled"],
        "allow_parallel_jobs": rj_json["allow_parallel_jobs"],
        "hook": hook.orchestrationhook_ptr,
    }
    rj, created = RecurringActionJob.objects.get_or_create(
        global_id=global_id,
        defaults=defaults)
    if not created:
        rj.hook = hook.orchestrationhook_ptr
        rj.save()
    return rj


def configure_inbound_webhooks():
    iwh_dir = f'{XUI_PATH}/inbound_webhooks/'
    try:
        iwhs = os.listdir(iwh_dir)
    except FileNotFoundError:
        logger.info(f"No inbound webhooks directory found at {iwh_dir}")
        return
    for iwh in iwhs:
        logger.info(f"Starting import of Inbound Webhook: {iwh}")
        iwh_file = f'{iwh}.json'
        iwh_path = f'{iwh_dir}{iwh}/{iwh_file}'
        with open(iwh_path, 'r') as f:
            iwh_json = json.load(f)
        hook_name = slugify(iwh_json["base_action_name"]).replace("-", "_")
        hook_json_path = f'{iwh_dir}{iwh}/{hook_name}/{hook_name}.json'
        with open(hook_json_path, 'r') as f:
            hook_json = json.load(f)
        script_filename = hook_json["script_filename"]
        hook_py_path = f'{iwh_dir}{iwh}/{hook_name}/{script_filename}'
        hook = create_cloudbolt_hook(hook_json, hook_py_path)
        create_inbound_webhook(iwh_json, hook)


def create_inbound_webhook(iwh_config, hook):
    global_id = iwh_config["id"]

    defaults = {
        "label": iwh_config["label"],
        "maximum_version_required": iwh_config["maximum_version_required"],
        "minimum_version_required": iwh_config["minimum_version_required"],
        "hook": hook.orchestrationhook_ptr,
    }
    iwh, created = InboundWebHook.objects.get_or_create(
        global_id=global_id,
        defaults=defaults)
    if not created:
        iwh.hook = hook.orchestrationhook_ptr
        iwh.save()
    return iwh


def configure_orchestration_hooks():
    oh_dir = f'{XUI_PATH}/orchestration_hooks/'
    try:
        ohs = os.listdir(oh_dir)
    except FileNotFoundError:
        logger.info(f"No Orchestration Hooks directory found at {oh_dir}")
        return
    for oh in ohs:
        logger.info(f"Starting import of Orchestration Hook: {oh}")
        iwh_file = f'{oh}.json'
        iwh_path = f'{oh_dir}{oh}/{iwh_file}'
        with open(iwh_path, 'r') as f:
            oh_json = json.load(f)
        oh_name = slugify(oh_json["base_action_name"]).replace("-", "_")
        oh_json_path = f'{oh_dir}{oh}/{oh_name}/{oh_name}.json'
        with open(oh_json_path, 'r') as f:
            hook_json = json.load(f)
        script_filename = hook_json["script_filename"]
        hook_py_path = f'{oh_dir}{oh}/{oh_name}/{script_filename}'
        hook = create_cloudbolt_hook(hook_json, hook_py_path)
        create_orchestration_hook(oh_json, hook)


def create_orchestration_hook(oh_config, hook):
    global_id = oh_config["id"]
    hp_id = HookPoint.objects.get(label=oh_config["hook_point"]).id
    defaults = {
        "continue_on_failure": oh_config["continue_on_failure"],
        "description": oh_config["description"],
        "enabled": oh_config["enabled"],
        "hook_point_id": hp_id,
        "maximum_version_required": oh_config["maximum_version_required"],
        "minimum_version_required": oh_config["minimum_version_required"],
        "name": oh_config["name"],
        "run_on_statuses": oh_config["run_on_statuses"],
        "run_seq": oh_config["run_seq"],
        "hook": hook.orchestrationhook_ptr,
    }
    oh, created = HookPointAction.objects.get_or_create(
        global_id=global_id,
        defaults=defaults)
    if not created:
        oh.hook = hook.orchestrationhook_ptr
        oh.save()
    return oh


def create_cloudbolt_hook(hook_config, hook_file):
    global_id = hook_config["id"]
    resource_technologies = hook_config["resource_technologies"]
    target_os_families = hook_config["target_os_families"]
    defaults = {
        "name": hook_config["name"],
        "description": hook_config["description"],
        "max_retries": hook_config["max_retries"],
        "maximum_version_required": hook_config["maximum_version_required"],
        "minimum_version_required": hook_config["minimum_version_required"],
        "shared": hook_config["shared"],
        "module_file": hook_file,
        "ootb_module_file": hook_file,
    }
    hook, created = CloudBoltHook.objects.get_or_create(global_id=global_id,
                                                        defaults=defaults)
    if created or SET_ACTIONS_TO_REMOTE_SOURCE:
        hook.source_code_url = f'file://{hook_file}'
        hook.save()
        hook.fetch_remote_content()
        logger.info(f"Finished refreshing: {hook.name} from remote source")
    if resource_technologies:
        for rt_name in resource_technologies:
            rt = ResourceTechnology.objects.get(name=rt_name)
            hook.resource_technologies.add(rt)
    if target_os_families:
        for os_fam_name in target_os_families:
            os_fam = OSFamily.objects.get(name=os_fam_name)
            hook.os_families.add(os_fam)
    return hook
