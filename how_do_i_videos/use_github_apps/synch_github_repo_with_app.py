from datetime import datetime, timedelta
from jwt import encode as jwt_encode
from requests import Session
import os
import json
from common.methods import set_progress
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def run(job, **kwargs):
    app_id = '{{ github_app_id }}'
    private_key = """{{ github_private_key }}"""
    private_key = format_private_key(private_key)
    repo = '{{ github_repo }}'
    branch = '{{ github_branch }}'
    destination = '{{ destination_directory }}'
    logger.info(f"app_id: {app_id}")
    logger.info(f"repo: {repo}")
    logger.info(f"branch: {branch}")
    logger.info(f"destination: {destination}")

    if destination[-1] == '/':
        destination = destination[:-1]
    zip_file_path = f"/var/tmp/{repo.replace('/', '-')}.zip"
    repo_path = f'{destination}/{repo.replace("/", "-")}-{branch}'

    # Check to be sure that the repo is in the format: owner/repo
    if len(repo.split('/')) != 2:
        return "FAILURE", "", f"Repo must be in the format: owner/repo. " \
                              f"Repo provided: {repo}"
    # Check to be sure that the destination is a subdirectory to the proserv
    # directory
    if (not destination.startswith("/var/opt/cloudbolt/proserv/") or
            destination == "/var/opt/cloudbolt/proserv/" or
            destination == "/var/opt/cloudbolt/proserv"):
        return "FAILURE", "", ("destination must be a subdirectory of "
                               "/var/opt/cloudbolt/proserv/")

    with GitHubAppSession(app_id, private_key, repo=repo, branch=branch) as s:
        branch_sha = s.get_branch_sha()
        local_branch_sha = get_local_branch_sha(repo_path)
        logger.info(f"Branch sha: {branch_sha}")
        logger.info(f"Local branch sha: {local_branch_sha}")
        if branch_sha == local_branch_sha:
            set_progress("Branch has not changed, not downloading new zip.")
            return ("SUCCESS",
                    "Branch has not changed, not downloading new zip.", "")
        s.save_repo_zip_to_file(zip_file_path)

    repo_path = unzip_file(zip_file_path, destination, repo_path)
    save_local_branch_sha(repo_path, branch_sha)


def format_private_key(private_key):
    """
    replace all spaces with newlines for the private key except for the
    first and last lines
    :param private_key: The private key to format
    """
    # Strip the first and last lines of a private key
    key_data = private_key[31:-29]
    # Replace all spaces with newlines
    key_data = key_data.replace(' ', '\n')
    # Add the first and last lines back
    private_key = f"{private_key[0:31]}{key_data}{private_key[-29:]}"
    return private_key


class GitHubAppSession(Session):
    """This class manages interacting with the GitHub api as a GitHub App.
    Using your app's id and private pem we craft a Json Web Token (jwt) to
    request an access token that lets us work with the api.
    After this object has authenticated just use the request.Session package's
    methods to preform your requests.

    Should be used as a context manager.
    """

    def __init__(self, app_id, private_key, installation_id=None, username=None,
                 org=None, repo=None, branch="main"):
        super(GitHubAppSession, self).__init__()
        self.headers.update({'User-Agent': 'CloudBolt GitHub Application'})
        self.headers.update({'Accept': 'application/vnd.github+json'})
        self.base_url = 'https://api.github.com'
        self.app_id = app_id
        self.pk = private_key
        self.jwt = None
        self.token_expires_at = None
        self.branch = branch
        # One of the following must be provided. If more than one is provided
        # the order of precedence is: installation_id, org, username, repo
        self.installation_id = installation_id
        self.username = username
        self.org = org
        # If used, repo should be in the format: {owner}/{repo}
        self.repo = repo

    def update_bearer(self, bearer_token):
        self.headers.update({
            'Authorization': f'Bearer {bearer_token.decode("ascii")}'}
        )

    def update_auth(self, auth_token):
        self.headers.update({'Authorization': 'token {}'.format(auth_token)})

    def update_agent(self, agent_string):
        self.headers.update({'User-Agent': '{}'.format(agent_string)})

    def create_jwt(self):
        payload = {
            # Issued at time
            'iat': int(datetime.now().timestamp()),
            # JWT expiration time (10 minute maximum)
            'exp': int((datetime.now() + timedelta(minutes=9)).timestamp()),
            # GitHub App's identifier
            'iss': self.app_id,
            'alg': 'RS256'
        }
        return jwt_encode(payload, self.pk, algorithm='RS256')

    def request_token(self):
        resp = None
        if self.installation_id:
            url = (f"{self.base_url}/app/installations/{self.installation_id}/"
                   f"access_tokens")
            resp = self.post(url)
            if resp.status_code == 201:
                self.update_auth(resp.json().get('token'))
                self.token_expires_at = datetime.strptime(
                    resp.json().get('expires_at'), '%Y-%m-%dT%H:%M:%SZ'
                )
            else:
                raise Exception(resp.content)

    def __enter__(self):
        self.jwt = self.create_jwt()
        self.update_bearer(self.jwt)
        if not self.installation_id:
            app_installation = self.get_app_installation()
            self.installation_id = app_installation["id"]
        self.request_token()
        return self

    def __exit__(self, *args):
        self.close()

    def get_app_installation(self):
        # Per the docs, this should either be: /users/{username}/installation,
        # /orgs/{org}/installation, /repos/{owner}/{repo}/installation,
        # or /app/installations

        if self.org:
            url = f"{self.base_url}/orgs/{self.org}/installation"
        elif self.username:
            url = f"{self.base_url}/users/{self.username}/installation"
        elif self.repo:
            url = f"{self.base_url}/repos/{self.repo}/installation"

        resp = self.get(url)
        return resp.json()

    def get_repo_zip(self):
        # Not passing a repo will use the repo provided when the object was
        # instantiated.
        url = f"{self.base_url}/repos/{self.repo}/zipball/{self.branch}"
        resp = self.get(url)
        return resp.content

    def save_repo_zip_to_file(self, file_path):
        """
        Saves a zip file of the repo to the specified file path.
        Not passing a repo will use the repo provided when the object was
        instantiated.
        :param file_path: The path to save the zip file to. Ex: /tmp/my_repo.zip
        :param repo: The repo to download. Should be in the format:
            {owner}/{repo}
        :param branch: The branch to download. Defaults to main.
        :return: The path to the file.
        """
        if not file_path.endswith('.zip'):
            raise Exception("file_path must be a zip file")
        dir_path = "/".join(file_path.split('/')[0:-1])
        mkdir_p(dir_path)
        resp = self.get_repo_zip()
        with open(file_path, 'wb') as f:
            f.write(resp)
        return file_path

    def get_branch(self):
        """
        Get a branch from a repo
        :return:
        """
        url = f"{self.base_url}/repos/{self.repo}/branches/{self.branch}"
        return self.get(url).json()

    def get_branch_sha(self):
        """
        Get the sha for a branch in the repo
        :return:
        """
        branch = self.get_branch()
        return branch["commit"]["sha"]


def mkdir_p(path):
    import errno
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def unzip_file(file_path, destination, repo_path):
    """
    Unzips a file to the specified destination. will delete the zip file after
    unzipping. Will also delete the destination directory recursively if it
    already exists.
    :param file_path: The path to the zip file. Ex: /tmp/my_repo.zip
    :param destination: The path to move the unzipped repo to. Must be a
        subdirectory of /var/opt/cloudbolt/proserv/.
        Ex: /var/opt/cloudbolt/proserv/my_repo
    :param repo: The repo to download. Should be in the format: {owner}/{repo}
    :return: The path to the unzipped repo.
    """
    import zipfile

    # Check to be sure that the destination is a subdirectory to the proserv
    # directory
    if (not destination.startswith("/var/opt/cloudbolt/proserv/") or
            destination == "/var/opt/cloudbolt/proserv/" or
            destination == "/var/opt/cloudbolt/proserv"):
        return "FAILURE", "", ("destination must be a subdirectory of "
                               "/var/opt/cloudbolt/proserv/")

    # Unzip the file
    unzip_path = "/var/tmp"
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        relative_path, = zipfile.Path(zip_ref).iterdir()
        root_dir = f'{unzip_path}/{relative_path.name}'
        zip_ref.extractall(unzip_path)
    # Delete the zip file
    os.remove(file_path)
    # Set the repo name and final path repo of test/test will end up being
    # test-test

    # If a directory exists at the path already delete it recursively
    if os.path.exists(repo_path):
        import shutil
        import getpass
        logger.debug("Effective user is [%s]" % (getpass.getuser()))
        shutil.rmtree(repo_path)
    # Ensure that the parent directory exists
    mkdir_p(destination)
    # Move and rename the root_dir - GitHub zips have a root dir that is the
    # repo name and sha, want to rename this to just the repo name and move it
    # to the correct destination.
    os.rename(root_dir, repo_path)

    return repo_path


def get_local_branch_sha(repo_path):
    """
    If a branch_sha.json file exists in the destination folder, load the file
    contents with json and return the sha from that file. Otherwise, return None
    :repo_path: The path to the repo directory
    :return:
    """
    branch_sha_file = f"{repo_path}/branch_sha.json"
    if os.path.exists(branch_sha_file):
        with open(branch_sha_file, 'r') as f:
            return json.load(f)['sha']
    else:
        return None


def save_local_branch_sha(repo_path, branch_sha):
    """
    Saves a json file containing the branch sha to the destination folder
    :param repo_path: The path to the repo directory
    :param branch_sha: The sha of the branch to save
    :return:
    """

    branch_sha_file = f"{repo_path}/branch_sha.json"
    with open(branch_sha_file, 'w') as f:
        json.dump({'sha': branch_sha}, f)
    return branch_sha_file


def chown_directory_recursively(directory):
    """
    Recursively chown the directory to the cloudbolt user
    :param directory: The directory to chown
    """
    import pwd
    import grp
    import getpass
    logger.debug("Env thinks the user is [%s]" % (os.getlogin()))
    logger.debug("Effective user is [%s]" % (getpass.getuser()))
    uid = pwd.getpwnam('cloudbolt').pw_uid
    gid = grp.getgrnam('cloudbolt').gr_gid
    os.chown(directory, uid, gid)
    for root, dirs, files in os.walk(directory):
        for d in dirs:
            os.chown(os.path.join(root, d), uid, gid)
        for f in files:
            os.chown(os.path.join(root, f), uid, gid)
