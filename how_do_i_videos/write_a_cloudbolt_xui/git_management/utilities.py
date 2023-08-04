import base64
import json
import os
import urllib

import requests
from urllib.parse import urlencode
from django.utils.text import slugify
from requests import HTTPError

from accounts.models import UserProfile
from c2_wrapper import create_custom_field
from cbhooks.models import ServerAction, HookPointAction
from extensions.models import UIExtension
from jobs.models import RecurringJob
from servicecatalog.models import ServiceBlueprint
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def get_all_blueprints():
    bps = ServiceBlueprint.objects.filter(status="ACTIVE")
    bps = bps.exclude(name="Custom Server")
    return bps.order_by('name')


def get_documentation():
    return """
    <h2>Git Management</h2>
    <ol>
    The Git Management extension allows you to export content from CloudBolt
    to a Git Repo. This extension is designed to work with either GitHub or 
    GitLab.
    </ol>
    <h3>Initial Setup</h3>
    <ol><li><strong>1.</strong> Gather a Personal Access Token for your user 
    account from GitHub or GitLab. The token must have the appropriate 
    permissions to read the Git repo and create commits in the Git Repo.
    <br>&nbsp;&nbsp;&nbsp;&nbsp;
    <strong> - GitHub required permissions:</strong> read, write on the repo in 
    question
    <br>&nbsp;&nbsp;&nbsp;&nbsp;
    <strong> - GitLab required permissions:</strong> api, read_api
    </li>
    <li>
    <strong>2.</strong> Create a Git Management XUI configuration for each Git 
    Repo/Branch you want to export content to. The name of the configuration 
    will be used to identify the configuration in the Git Management XUI.
    </li>
    <li>
    <strong>3.</strong> Choose the tab for the type of content you would like to
    export to Git. Select to either commit multiple items or commit a single 
    item.
    </li>
    </ol>
    <h3>Notes</h3>
    <ol>
    Committing content may take a while to refresh the page depending on how 
    much and what kind of content was committed. Please be patient.
    </ol>
"""


def create_git_commit_from_content(content_type, content_id, git_config_name,
                                   git_comment, user):
    """
    An abstracted function that will select the appropriate Git endpoint based
    off of the Git Management XUI configuration data and then call the
    appropriate function to create the commit.
    :param content_type: the type of content to create the commit for
    :param content_id: the id of the content to create the commit for
    :param git_config_name: the name of the Git Management XUI configuration
    :param git_comment: the comment to use for the commit
    :param user: the user to create the commit for
    """
    git_configs = GitManagementConfigs(user, "git_config")
    git_config = git_configs.get_git_config_by_name(git_config_name)
    git_auth_token_name = git_config["git_auth_token_name"]
    git_tokens = GitManagementConfigs(user, "git_tokens")
    git_auth_token = git_tokens.get_git_config_by_name(git_auth_token_name)
    git_type = git_auth_token["git_type"]
    if git_type == "github":
        wrapper = GitHubWrapper(user, git_config)
    elif git_type == "gitlab":
        wrapper = GitLabWrapper(user, git_config)
    else:
        raise Exception(f"Git Type {git_type} is not supported")
    if not wrapper:
        raise Exception(f"Wrapper could not be determined for type: {git_type}"
                        f", user:{user}, and config: {git_config}")
    logger.info(f"Creating commit for {content_type} {content_id} with "
                f"comment {git_comment}")
    return wrapper.create_git_commit_from_content(content_type, content_id,
                                                  git_comment)


class GitManagementConfigs(object):
    """
    Wrapper for accessing and working with Git Management Configs.
    There are two types of configs:
    1. git_config: the actual configuration data for the Git Management XUI
    2. git_tokens: the auth tokens for the Git Management XUI
    """

    def __init__(self, user, record_type):
        """
        :param user: the user to get the config data for
        :param record_type: the type of config data to get (git_config or
            git_tokens)
        """
        assert isinstance(user, UserProfile), f'{user} is not of the type ' \
                                              f'UserProfile'
        self.user = user
        if record_type not in ["git_config", "git_tokens"]:
            raise Exception("record_type must be git_config or git_tokens")
        self.record_type = record_type

    def get_config_data(self):
        """
        Create a CustomField for the configuration data for the GitHub
        Management XUI
        :return: the CustomField, CustomFieldValue, and the config data as a
        tuple
        """
        if self.record_type == "git_config":
            cf = create_custom_field("git_management_config_data",
                                     "Git Configuration Data",
                                     "TXT",
                                     namespace="git_management",
                                     description="GitHub Management XUI Config"
                                                 " Data",
                                     show_on_servers=True,
                                     )
        elif self.record_type == "git_tokens":
            cf = create_custom_field("git_auth_token_data",
                                     "Git Auth Token Data",
                                     "ETXT",
                                     namespace="git_management",
                                     description="GitHub Management XUI Auth"
                                                 " Token Data",
                                     show_on_servers=True,
                                     )
        cfvs = self.user.get_cfvs_for_custom_field(cf.name)
        if len(cfvs) > 1:
            raise Exception("More than one CustomFieldValue found for "
                            "git_management_config_data. Please delete all but "
                            "one.")
        elif len(cfvs) == 1:
            cfv = cfvs[0]
        else:
            # Need to create the CustomFieldValue with the user included to
            # guarantee that this will be a unique CustomFieldValue for the user
            value_str = {"user": self.user.username}
            value = json.dumps(value_str)
            cfv, _ = self.user.custom_field_values.get_or_create(field=cf,
                                                                 value=value)
        config_data = json.loads(cfv.value)
        return cf, cfv, config_data

    def set_config_data(self, new_data):
        """
        Set the config data for the GitHub Management XUI
        :param new_data: the new data to set type: dict
        :return: None
        """
        new_data = json.dumps(new_data)
        _, cfv, _ = self.get_config_data()
        cfv.value = new_data
        cfv.save()

    def get_git_configs(self):
        """
        Get the git configurations from the CustomField
        :return: the git configurations as a list of dicts
        """
        _, _, config_data = self.get_config_data()
        configs = []
        for k, v in config_data.items():
            if k != "user":
                configs.append(v)
        return configs

    def get_git_config_by_name(self, config_name):
        """
        Get the git configuration from the CustomField
        :param config_name: the name of the config to get
        :return: the git configuration as a dict
        """
        _, _, git_configs = self.get_config_data()
        git_config = git_configs[config_name]
        return git_config

    def delete_git_config(self, config_name):
        """
        Delete the git configuration from the CustomField
        :param config_name: the name of the config to delete
        :return: None
        """
        _, _, config_data = self.get_config_data()
        if config_name in config_data:
            del config_data[config_name]
        self.set_config_data(config_data)

    def add_or_edit_git_config(self, config_name, config_type, repo, branch,
                               git_auth_token_name, root_directory):
        """
        Add a new or edit an existing git configuration on the CustomField
        :param config_name: the name of the config to add
        :param config_type: the type of the config to add
        :param repo: the repo of the config to add
        :param branch: the branch of the config to add
        :param git_auth_token_name: the git auth token to associate with the config
        :param root_directory: the root directory in the git repo to export to
        :return: None
        """
        _, _, config_data = self.get_config_data()
        if not root_directory:
            root_directory = ""
        config = {
            "name": config_name,
            "config_type": config_type,
            "repo": repo,
            "branch": branch,
            "git_auth_token_name": git_auth_token_name,
            "root_directory": root_directory
        }
        config_data[config_name] = config
        self.set_config_data(config_data)

    def add_or_edit_git_token(self, token_name, git_type, token, api_url):
        """
        Add a new or edit an existing git token on the CustomField
        :param token_name: the name of the token config to add
        :param git_type: the type of the config to add - GitHub or gitlab
        :param token: the token to associate with the config
        :param api_url: the api url to associate with the config
        :return: None
        """
        _, _, config_data = self.get_config_data()
        config = {
            "name": token_name,
            "git_type": git_type,
            "token": token,
            "api_url": api_url
        }
        config_data[token_name] = config
        self.set_config_data(config_data)


def get_root_content_directory(root_directory, content_type):
    """
    Generate the path to the root directory for the content type. This ends up
    being the root_directory + content_type name. For example, if the
    root_directory in GitHub is cloudbolt_content/ the content_type is
    ServiceBlueprint - this will return "cloudbolt_content/blueprints"
    :param root_directory: the git config to get the root directory from
    :param content_type: the type of content to get the root directory for
    """
    if root_directory:
        if root_directory[-1] != "/":
            root_directory += "/"
    content_directory = get_content_directory_for_type(content_type)
    root_directory += f'{content_directory}'
    return root_directory


def get_content_choices(content_type):
    choices = None
    if content_type == "ServiceBlueprint":
        content = get_all_blueprints()
        choices = format_bps_for_template(content)
    elif content_type == "ServerAction":
        content = get_all_server_actions()
        choices = format_server_actions_for_template(content)
    elif content_type == "HookPointAction":
        content = get_all_orchestration_actions()
        choices = format_orch_actions_for_template(content)
    elif content_type == "RecurringJob":
        content = get_all_recurring_jobs()
        choices = format_recurring_jobs_for_template(content)
    elif content_type == "UIExtension":
        content = get_all_xuis()
        choices = format_xuis_for_template(content)
    if not choices:
        raise Exception(f"Content type {content_type} is not supported")
    return [(c["global_id"], c["label"]) for c in choices]


def get_content_directory_for_type(content_type):
    content_map = {
        "ServiceBlueprint": "blueprints",
        "ServerAction": "server-actions",
        "HookPointAction": "orchestration-actions",
        "RecurringJob": "recurring-jobs",
        "UIExtension": "ui-extension-packages",
    }
    return content_map[content_type]


def export_content_to_tmp_dir(content_type, content_id):
    # Get the content from CloudBolt
    function_string = f'{content_type}.objects.get(global_id="{content_id}")'

    # Export the content in supported format to a /tmp directory
    export_call = f'export_{content_type.lower()}({function_string})'
    tmp_dir = eval(export_call)

    return tmp_dir


def delete_tmp_dir(tmp_dir):
    import shutil
    shutil.rmtree(tmp_dir)


def export_serviceblueprint(bp):
    from servicecatalog.api.v3.serializers import ServiceBlueprintSerializer
    serializer = ServiceBlueprintSerializer()
    tmp_dir = serializer.export_to_filesystem_as_unzipped_files(
        bp, include_zip=False)
    return tmp_dir


def export_serveraction(sa):
    from cbhooks.api.v3.serializers import ServerActionSerializer
    serializer = ServerActionSerializer()
    tmp_dir = serializer.export_to_filesystem_as_unzipped_files(
        sa, include_zip=False)
    return tmp_dir


def export_hookpointaction(hpa):
    from cbhooks.api.v3.serializers import OrchestrationActionSerializer
    serializer = OrchestrationActionSerializer()
    tmp_dir = serializer.export_to_filesystem_as_unzipped_files(
        hpa, include_zip=False)
    return tmp_dir


def export_recurringjob(rj):
    from cbhooks.api.v3.serializers import RecurringActionJobSerializer
    serializer = RecurringActionJobSerializer()
    tmp_dir = serializer.export_to_filesystem_as_unzipped_files(
        rj.cast(), include_zip=False)
    return tmp_dir


def export_uiextension(xui):
    from extensions.api.v3.serializers import UIExtensionSerializer
    serializer = UIExtensionSerializer()
    tmp_dir = serializer.export_to_filesystem_as_unzipped_files(
        xui, include_zip=False)
    return tmp_dir


def get_all_orchestration_actions():
    """
    Get all orchestration actions
    """
    orch_actions = HookPointAction.objects.filter(
        hook_point__triggerpoint__isnull=True).order_by('name')
    return orch_actions


def get_all_rules():
    """
    Get all CloudBolt Rules
    """
    rules = HookPointAction.objects.filter(
        hook_point__triggerpoint__isnull=False).order_by('name')
    return rules


def get_all_server_actions():
    """
    Get all server actions
    """
    return ServerAction.objects.all().order_by('label')


def get_all_recurring_jobs():
    """
    Get all recurring jobs
    """
    return RecurringJob.objects.all().order_by('name')


def get_all_xuis():
    """
    Get all XUIs
    """
    return UIExtension.objects.all().order_by('label')


def format_bps_for_template(bps):
    formatted_bps = []
    for bp in bps:
        rt = bp.resource_type.label if bp.resource_type else "None"
        bp_data = {
            "global_id": bp.global_id,
            "label": bp.name,
            "column_1_data": rt,
        }
        formatted_bps.append(bp_data)
    return formatted_bps


def format_server_actions_for_template(server_actions):
    formatted_actions = []
    for action in server_actions:
        action_data = {
            "global_id": action.global_id,
            "label": action.label,
        }
        formatted_actions.append(action_data)
    return formatted_actions


def format_orch_actions_for_template(orch_actions):
    formatted_actions = []
    for action in orch_actions:
        action_data = {
            "global_id": action.global_id,
            "label": action.name,
            "column_1_data": action.hook_point.label,
        }
        formatted_actions.append(action_data)
    return formatted_actions


def format_recurring_jobs_for_template(recurring_jobs):
    formatted_jobs = []
    for job in recurring_jobs:
        job_data = {
            "global_id": job.global_id,
            "label": job.name,
            "column_1_data": job.type_display(),
        }
        formatted_jobs.append(job_data)
    return formatted_jobs


def format_xuis_for_template(xuis):
    formatted_xuis = []
    for xui in xuis:
        action_data = {
            "global_id": xui.global_id,
            "label": xui.name,
            "column_1_data": xui.filepath,
        }
        formatted_xuis.append(action_data)
    return formatted_xuis


class GitHubWrapper(object):
    """
    Wrapper for the GitHub API
    """

    def __init__(self, user, git_config):
        """
        :param git_config: GitManagementConfig object
        :param user: CloudBolt User object
        """
        self.git_config = git_config
        self.git_auth_token_name = self.git_config["git_auth_token_name"]
        self.git_token_config = GitManagementConfigs(
            user, "git_tokens").get_git_config_by_name(self.git_auth_token_name)
        self.token = self.git_token_config["token"]
        self.repo = self.git_config["repo"]
        self.branch = self.git_config["branch"]
        self.root_directory = self.git_config["root_directory"]
        self.github_api_version = "2022-11-28"
        api_url = self.git_token_config["api_url"]
        if api_url.endswith("/"):
            api_url = api_url[:-1]
        if not api_url.startswith("https://"):
            api_url = f"https://{api_url}"
        self.base_url = api_url
        self.verify = True

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

    def _request(self, url, method="GET", data=None):
        """
        Return the json of a Request to the GitHub API
        """
        headers = {
            "Authorization": f"token {self.token}",
            "X-GitHub-Api-Version": self.github_api_version,
            "Accept": "application/vnd.github+json"
        }
        request_url = f"{self.base_url}{url}"
        r = requests.request(
            method,
            request_url,
            headers=headers,
            json=data,
            verify=self.verify,
        )

        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            err_message = e.response.json()["message"]
            logger.error(f"Error: {e}")
            logger.error(f"Error Message: {err_message}")
            raise e
        return r.json()

    def get_repos(self):
        """
        Query the GitHub API and return a list of repos for the user
        :return:
        """
        url = f"/user/repos"
        return self.get(url)

    def get_branches_for_repository(self):
        """
        Query the GitHub API and return a list of branches for the repo in the
        config
        :return:
        """
        url = f"/repos/{self.repo}/branches"
        return self.get(url)

    def create_or_update_file_contents(
            self,
            path,
            content,
            user=None,
            message="Update file by CloudBolt Git Management XUI"
    ):
        """
        Create or update a file in the repo
        :param path: The path to the file. ex. "test/test.txt"
        :param message: The commit message
        :param content: The content of the file in plain text
        :param user: The user to commit as - this is the CloudBolt user object
        :return:
        """
        url = f"/repos/{self.repo}/contents/{path}"
        content_bytes = content.encode("ascii")
        base64_bytes = base64.b64encode(content_bytes)
        base64_content = base64_bytes.decode("ascii")
        data = {
            "message": message,
            "content": base64_content,
            "branch": self.branch,
        }
        if user:
            committer = {
                "name": f'{user.first_name} {user.last_name}',
                "email": user.email,
            }
            data["committer"] = committer
        return self.put(url, data)

    def delete_file(
            self,
            path,
            user=None,
            message="Delete file by CloudBolt Git Management XUI"
    ):
        """
        Delete a file in the repo
        :param path: The path to the file. ex. "test/test.txt"
        :param message: The commit message
        :param user: The user to commit as - this is the CloudBolt user object
        :return:
        """
        url = f"/repos/{self.repo}/contents/{path}"
        data = {
            "message": message,
            "branch": self.branch,
            "sha": self.get_sha_for_file(path),
        }
        if user:
            committer = {
                "name": f'{user.first_name} {user.last_name}',
                "email": user.email,
            }
            data["committer"] = committer
        return self.delete(url, data)

    def get_repository_content(self, path):
        """
        Get the contents of a repository starting at a file or directory
        :param path: The path to the file or directory. ex. "test/test.txt"
        :return:
        """
        url = f"/repos/{self.repo}/contents/{path}?ref={self.branch}"
        return self.get(url)

    def get_sha_for_file(self, path):
        """
        Get the sha for a file in the repo
        :param path: The path to the file. ex. "test/test.txt"
        :return:
        """
        contents = self.get_repository_content(path)
        if type(contents) is list:
            raise Exception(f"Path {path} is a directory")
        return contents["sha"]

    def get_branch(self):
        """
        Get a branch from a repo
        :return:
        """
        url = f"/repos/{self.repo}/branches/{self.branch}"
        return self.get(url)

    def get_branch_sha(self):
        """
        Get the sha for a branch in the repo
        :return:
        """
        branch = self.get_branch()
        return branch["commit"]["sha"]

    def create_blob(self, content):
        """
        Create a blob in the repo
        :param content: The content of the file in plain text
        :return: The sha of the blob
        """
        url = f"/repos/{self.repo}/git/blobs"
        file_content_encoded = base64.b64encode(content)
        data = {
            "content": file_content_encoded,
            "encoding": "base64",
        }
        return self.post(url, data)["sha"]

    def get_tree_sha_from_path(self, tree_path):
        """
        Get the sha of a tree from a path
        :param tree_path: The path to the tree ex. "parent/child"
        :return: The sha of the tree
        """
        dir_name = tree_path.split('/')[-1]
        parent_path = '/'.join(tree_path.split('/')[:-1])
        # With the Contents API, we have to get the parent directory then loop
        # through each tree in the directory to get the tree we are looking for
        # This is because the trees API does not support getting a tree by path
        contents = self.get(f"/repos/{self.repo}/contents/{parent_path}")
        for content in contents:
            if content["type"] == "dir" and content["name"] == dir_name:
                return content["sha"]
        return None

    def get_tree(self, tree_sha, query_params: list[dict] = None):
        """
        Get a tree from the repo
        :param tree_sha: The sha of the tree
        :param query_params: A list of query param dicts to add to the request
            ex. [{"recursive": "true"}]
        :return: The tree
        """
        url = f"/repos/{self.repo}/git/trees/{tree_sha}"
        if query_params:
            url += f"?{'&'.join([urlencode(p) for p in query_params])}"
        return self.get(url)

    def create_tree(self, base_tree_sha, tree: list[dict]):
        """
        Create a tree in the repo
        :param base_tree_sha: The sha of the base tree
        :param tree: A list of trees to create
        """
        url = f"/repos/{self.repo}/git/trees"
        data = {
            "base_tree": base_tree_sha,
            "tree": tree,
        }
        return self.post(url, data)["sha"]

    def create_commit(self, message, tree_sha, parent_sha):
        """
        Create a commit in the repo
        :param message: The commit message
        :param tree_sha: The sha of the tree
        :param parent_sha: The sha of the parent commit
        """
        url = f"/repos/{self.repo}/git/commits"
        data = {
            "message": message,
            "tree": tree_sha,
            "parents": [parent_sha],
        }
        return self.post(url, data)["sha"]

    def get_commit(self, commit_sha):
        """
        Get a commit from the repo
        :param commit_sha: The sha of the commit
        """
        url = f"/repos/{self.repo}/commits/{commit_sha}"
        return self.get(url)

    def update_branch_ref(self, commit_sha):
        """
        Update a branch ref in the repo
        :param commit_sha: The sha of the commit
        """
        url = f"/repos/{self.repo}/git/refs/heads/{self.branch}"
        data = {
            "sha": commit_sha,
        }
        return self.patch(url, data)["url"]

    def get_sorted_list_of_repos(self):
        """
        Get the list of repos for the GitHub endpoint
        :return: the list of repos
        """
        repos = self.get_repos()
        return sorted(r["full_name"] for r in repos)

    def get_sorted_list_of_branches(self):
        """
        Get the list of branches for the GitHub endpoint
        :return: the list of branches
        """
        branches = self.get_branches_for_repository()
        return sorted(b["name"] for b in branches)

    def create_git_commit_from_content(self, content_type, content_id,
                                       git_comment):
        """
        Create a git commit from the CloudBolt content
        :param content_type: the type of the content to export
        :param content_id: the id of the content to export
        :param git_comment: the comment to use for the git commit
        :return: The id for the git commit
        """
        # Get the content from CloudBolt
        tmp_dir = export_content_to_tmp_dir(content_type, content_id)

        # Create the git commit
        ref_url = self.create_commit_from_directory(tmp_dir, git_comment,
                                                    content_type)

        # Delete the tmp directory
        delete_tmp_dir(tmp_dir)

        return ref_url

    def create_commit_from_directory(self, tmp_dir, git_comment, content_type):
        root_content_directory = get_root_content_directory(self.root_directory,
                                                            content_type)
        branch_sha = self.get_branch_sha()
        tree_sha = self.create_tree_from_directory(tmp_dir,
                                                   root_content_directory,
                                                   branch_sha)
        commit_sha = self.create_commit(git_comment, tree_sha, branch_sha)
        ref_url = self.update_branch_ref(commit_sha)
        html_url = self.get_commit(commit_sha)["html_url"]
        return html_url

    def create_tree_from_directory(self, tmp_dir, root_content_directory,
                                   branch_sha):
        logger.info(f"Creating tree from directory {tmp_dir}")
        tree = []
        content_dir = slugify(tmp_dir.split("/")[-1]).replace('-', '_')
        content_dir = f'{root_content_directory}/{content_dir}'
        for root, dirs, files in os.walk(tmp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_content = open(file_path, 'rb').read()
                git_file_path = file_path.replace(tmp_dir, content_dir)
                blob_sha = self.create_blob(file_content)
                tree.append({
                    "path": git_file_path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha
                })
        tree = self.update_tree_to_remove_deleted_files(tree, content_dir)
        return self.create_tree(branch_sha, tree)

    def update_tree_to_remove_deleted_files(self, tree, content_dir):
        """
        Remove files from the tree that have been deleted from the CloudBolt content
        We only want to impact files that are in the content directory. We don't
        want to remove files that are in any directories outside the content dir.
        :param tree: the tree to update
        :param content_dir: the root directory for the content
        """
        current_tree_sha = self.get_tree_sha_from_path(content_dir)
        if not current_tree_sha:
            # If the dir (tree) doesn't already exist there wouldn't be any files
            # to remove. Just return the original tree that we built.
            return tree
        query_params = [{"recursive": "true"}]
        current_tree = self.get_tree(current_tree_sha, query_params)
        new_tree_files = [f["path"] for f in tree]
        for item in current_tree["tree"]:
            if item["type"] == "blob":
                tree_path = f'{content_dir}/{item["path"]}'
                if tree_path not in new_tree_files:
                    logger.info(
                        f"Removing file {tree_path} from tree - it does not"
                        f" exist in the new tree")
                    tree.append({
                        "path": tree_path,
                        "mode": item["mode"],
                        "type": item["type"],
                        "sha": None,
                    })
        return tree


class GitLabWrapper(object):
    """
    Wrapper for the GitLab API
    """

    def __init__(self, user, git_config):
        """
        :param git_config: GitManagementConfig object
        :param user: CloudBolt User object
        """
        self.git_config = git_config
        self.git_auth_token_name = self.git_config["git_auth_token_name"]
        self.git_token_config = GitManagementConfigs(
            user, "git_tokens").get_git_config_by_name(self.git_auth_token_name)
        self.token = self.git_token_config["token"]
        self.repo = self.git_config["repo"]
        self.project_path = urllib.parse.quote(self.repo, safe='')
        self.branch = self.git_config["branch"]
        self.root_directory = self.git_config["root_directory"]
        api_url = self.git_token_config["api_url"]
        if api_url.endswith("/"):
            api_url = api_url[:-1]
        if not api_url.startswith("https://"):
            api_url = f"https://{api_url}"
        self.base_url = f'{api_url}/api/v4'
        self.verify = True

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

    def _request(self, url, method="GET", data=None):
        """
        Return the json of a Request to the GitHub API
        """
        headers = {
            'PRIVATE-TOKEN': self.token,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        request_url = f"{self.base_url}{url}"
        r = requests.request(
            method,
            request_url,
            headers=headers,
            json=data,
            verify=self.verify,
        )

        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            response_json = e.response.json()
            err_message = ""
            for key, value in response_json.items():
                err_message += f"{key}: {value}\n"
            logger.error(f"Error: {e}")
            logger.error(f"Error Message: {err_message}")
            raise e
        return r.json()

    def get_project(self):
        """
        Query the GitHub API and return the project for the repo in the config
        :return: the project object
        """
        url = f"/projects/{self.project_path}"
        return self.get(url)

    def get_branches_for_repository(self):
        """
        Query the GitHub API and return a list of branches for the repo in the
        config
        :return:
        """
        url = f"/projects/{self.project_path}/repository/branches"
        return self.get(url)

    def create_or_update_file_contents(
            self,
            path,
            content,
            user=None,
            message="Update file by CloudBolt Git Management XUI"
    ):
        """
        Create or update a file in the repo
        :param path: The path to the file. ex. "test/test.txt"
        :param message: The commit message
        :param content: The content of the file in plain text
        :param user: The user to commit as - this is the CloudBolt user object
        :return:
        """
        url = f"/repos/{self.repo}/contents/{path}"
        content_bytes = content.encode("ascii")
        base64_bytes = base64.b64encode(content_bytes)
        base64_content = base64_bytes.decode("ascii")
        data = {
            "message": message,
            "content": base64_content,
            "branch": self.branch,
        }
        if user:
            committer = {
                "name": f'{user.first_name} {user.last_name}',
                "email": user.email,
            }
            data["committer"] = committer
        return self.put(url, data)

    def delete_file(
            self,
            path,
            message="Delete file by CloudBolt Git Management XUI"
    ):
        """
        Delete a file in the repo
        :param path: The path to the file. ex. "test/test.txt"
        :param message: The commit message
        :param user: The user to commit as - this is the CloudBolt user object
        :return:
        """
        url = f"/projects/{self.project_path}/repository/files/{path}"
        data = {
            "commit_message": message,
            "branch": self.branch,
        }
        return self.delete(url, data)

    def get_branch(self):
        """
        Get a branch from a repo
        :return:
        """
        url = f"/projects/{self.project_path}/repository/branches/{self.branch}"
        return self.get(url)

    def get_branch_sha(self):
        """
        Get the branch sha for the branch in the config
        :return:
        """
        branch = self.get_branch()
        return branch["commit"]["id"]

    def create_git_commit_from_content(self, content_type, content_id,
                                       git_comment):
        """
        Create a git commit from the CloudBolt content
        :param content_type: the type of the content to export
        :param content_id: the id of the content to export
        :param git_comment: the comment to use for the git commit
        :return: The id for the git commit
        """
        # Get the content from CloudBolt
        tmp_dir = export_content_to_tmp_dir(content_type, content_id)

        # Create the git commit
        ref_url = self.create_commit_from_directory(tmp_dir, git_comment,
                                                    content_type)

        # Delete the tmp directory
        delete_tmp_dir(tmp_dir)

        return ref_url

    def create_commit_from_directory(self, tmp_dir, git_comment, content_type):
        root_content_directory = get_root_content_directory(self.root_directory,
                                                            content_type)

        actions = self.generate_actions_from_directory(tmp_dir,
                                                       root_content_directory)
        commit = self.create_commit(git_comment, actions)

        return commit["web_url"]

    def create_commit(self, git_comment, actions):
        """
        Create a commit in the repo
        :param git_comment: The comment to use for the commit
        :param actions: The actions to perform in the commit - should be a list
            of dictionaries
        :return: The sha of the commit
        """
        url = f"/projects/{self.project_path}/repository/commits"
        data = {
            "branch": self.branch,
            "commit_message": git_comment,
            "actions": actions,
        }
        return self.post(url, data)

    def generate_actions_from_directory(self, tmp_dir, root_content_directory):
        """
        Generate a list of actions to perform in the commit
        :param tmp_dir: The directory to generate the actions from
        :param root_content_directory: The root directory for the content
        """
        actions = []
        content_dir = slugify(tmp_dir.split("/")[-1]).replace('-', '_')
        content_dir = f'{root_content_directory}/{content_dir}'
        for root, dirs, files in os.walk(tmp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                git_file_path = file_path.replace(tmp_dir, content_dir)
                try:
                    # Check if the file exists in the repo
                    self.get_file(git_file_path)
                    action_mode = "update"
                except HTTPError as e:
                    logger.debug(f"File {git_file_path} does not exist in "
                                 f"repo. Creating.")
                    action_mode = "create"
                with open(file_path, "rb") as f:
                    content_bytes = f.read()
                    base64_bytes = base64.b64encode(content_bytes)
                    base64_content = base64_bytes.decode("ascii")
                    action = {
                        "action": action_mode,
                        "file_path": git_file_path,
                        "content": base64_content,
                        "encoding": "base64",
                    }
                    actions.append(action)
        actions = self.set_deleted_files(actions, content_dir)
        return actions

    def get_file(self, file_path):
        """
        Get a file from the repo
        :param file_path: The path to the file. ex. "test/test.txt"
        :return:
        """
        enc_file_path = urllib.parse.quote(file_path, safe='')
        url = f"/projects/{self.project_path}/repository/files/" \
              f"{enc_file_path}?ref={self.branch}"
        return self.get(url)

    def set_deleted_files(self, actions, content_dir):
        """
        Set files that have been deleted from the CloudBolt content directory to
        delete. We only want to impact files that are in the content directory.
        We don't want to remove files that are in any directories outside the
        content dir.
        :param actions: the actions list to update
        :param content_dir: the base path to the content directory
        """
        new_action_paths = [f["file_path"] for f in actions]
        tree = self.get_repository_tree(content_dir)
        for item in tree:
            if item["type"] != "blob":
                continue
            action_path = item["path"]
            if action_path not in new_action_paths:
                logger.info(
                    f"Removing file {action_path} from tree - it does not"
                    f" exist in the new tree")
                actions.append({
                    "action": "delete",
                    "file_path": action_path,
                })
        return actions

    def get_repository_tree(self, content_dir):
        """
        Get the tree for the repo recursively
        :param content_dir: the directory to get the tree for
        :return:
        """
        url = f"/projects/{self.project_path}/repository/tree" \
              f"?ref={self.branch}&path={content_dir}&recursive=true"
        return self.get(url)

