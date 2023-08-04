from django import forms
from django.contrib.auth.models import User
from django.forms import PasswordInput

from common.forms import C2Form
from common.widgets import SelectizeMultiple
from utilities.models import ConnectionInfo
from xui.git_management.utilities import get_content_choices, \
    GitManagementConfigs, create_git_commit_from_content
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


class GitConfigForm(C2Form):
    def __init__(self, *args, **kwargs):
        super(GitConfigForm, self).__init__(*args, **kwargs)
        initial = kwargs.get("initial", {})
        logger.debug(f'kwargs: {kwargs}')
        self.config_type = initial.get("config_type", None)
        if not self.config_type:
            raise ValueError("config_type must be specified")
        self.user = initial.get("user", None)
        if not self.user:
            raise ValueError("user must be specified")
        self.git_configs = GitManagementConfigs(self.user, self.config_type)
        self.fields["name"] = forms.CharField(
            max_length=50,
            required=True,
            initial=initial.get("name", None),
            help_text="Name of the GitHub Configuration"
        )
        git_tokens = GitManagementConfigs(self.user, "git_tokens")
        all_configs = git_tokens.get_git_configs()
        token_configs = [(c["name"], c["name"]) for c in all_configs]
        token_configs.insert(0, ("", "------Select a Git Auth Token------"))
        self.fields["git_auth_token_name"] = forms.ChoiceField(
            label="Git Auth Token",
            choices=token_configs,
            required=True,
            initial=initial.get("git_auth_token_name", None),
            help_text="Select a Git Auth Token",
            widget=forms.Select(attrs={"class": "form-control"})
        )
        self.fields["config_type"] = forms.ChoiceField(
            label="Config Type",
            choices=[("outbound", "outbound")],  # , ("inbound", "inbound")],
            required=True,
            initial=initial.get("type", None),
            help_text="Select a Repository Synch Direction for the "
                      "Configuration"
        )
        self.fields["repo"] = forms.CharField(
            label="Git Repository",
            max_length=100,
            required=True,
            initial=initial.get("repo", None),
            help_text="Enter a Repository to use for the Configuration. For "
                      "GitHub this should be in the format "
                      "'organization/repository', for GitLab this should be"
                      " in the format 'namespace/project_path'",
        )
        self.fields["branch"] = forms.CharField(
            label="Git Branch",
            max_length=100,
            required=True,
            initial=initial.get("branch", None),
            help_text="Enter a Branch to use for the Configuration"
        )
        self.fields["root_directory"] = forms.CharField(
            label="Root Directory",
            max_length=100,
            required=False,
            initial=initial.get("root_directory", None),
            help_text="Enter a Root directory for CloudBolt to synch content to"
        )

    def save(self):
        name = self.cleaned_data.get("name")
        git_auth_token_name = self.cleaned_data.get("git_auth_token_name")
        config_type = self.cleaned_data.get("config_type")
        repo = self.cleaned_data.get("repo")
        branch = self.cleaned_data.get("branch")
        root_directory = self.cleaned_data.get("root_directory")
        self.git_configs.add_or_edit_git_config(name, config_type, repo, branch,
                                                git_auth_token_name,
                                                root_directory)

        # Returns the name of the Git Config to be used as the success message
        return name


class GitTokenForm(C2Form):
    def __init__(self, *args, **kwargs):
        super(GitTokenForm, self).__init__(*args, **kwargs)
        initial = kwargs.get("initial", {})
        self.config_type = initial.get("config_type", None)
        if not self.config_type:
            raise ValueError("config_type must be specified")
        self.user = initial.get("user", None)
        if not self.user:
            raise ValueError("user must be specified")
        self.git_configs = GitManagementConfigs(self.user, self.config_type)
        self.fields["name"] = forms.CharField(
            max_length=50,
            required=True,
            initial=initial.get("name", None),
            help_text="Name of the GitHub Token"
        )
        self.fields["git_type"] = forms.ChoiceField(
            label="Git Provider Type",
            choices=[("github", "github"), ("gitlab", "gitlab")],
            required=True,
            initial=initial.get("git_type", None),
            help_text="Select a Git Provider Type",
            widget=forms.Select()
        )
        self.fields["api_url"] = forms.CharField(
            label="API URL",
            max_length=100,
            required=True,
            initial=initial.get("api_url", None),
            help_text="Base URL for the Git Provider API. GitHub should almost "
                      "always be https://api.github.com. GitLab should be "
                      "https://gitlab.com unless you have a custom domain.",
        )
        self.fields["token"] = forms.CharField(
            label="Personal Access Token",
            required=True,
            initial=initial.get("token", None),
            help_text="Enter a Personal Access Token for the Git Provider, "
                      "with read and write permissions on the repositories "
                      "you want to synch",
            widget=PasswordInput(render_value=True)
        )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self):
        token_name = self.cleaned_data.get("name")
        git_type = self.cleaned_data.get("git_type")
        token = self.cleaned_data.get("token")
        api_url = self.cleaned_data.get("api_url")
        self.git_configs.add_or_edit_git_token(token_name, git_type, token,
                                               api_url)

        # Returns the name of the Git Config to be used as the success message
        return token_name


class GitCommitForm(C2Form):
    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", {})
        super_kwargs = {"initial": initial}
        super(GitCommitForm, self).__init__(*args, **super_kwargs)
        self.user = initial.get("user", None)

        self.fields["content_type"] = forms.CharField(
            label="Content Type",
            max_length=50,
            required=True,
            initial=initial.get("content_type", None),
            widget=forms.TextInput(attrs={"readonly": True})
        )
        self.fields["content_id"] = forms.CharField(
            label="Content Global ID",
            max_length=50,
            required=True,
            initial=initial.get("content_id", None),
            widget=forms.TextInput(attrs={"readonly": True})
        )
        self.fields["git_config"] = forms.ChoiceField(
            label="Git Config",
            choices=self.format_outbound_configs(),
            required=True,
            help_text="Select a Git Config for the Commit",
        )
        self.fields["git_comment"] = forms.CharField(
            label="Git Comment",
            max_length=500,
            required=True,
            help_text="Enter the comment to be sent with the commit",
            widget=forms.Textarea
        )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self):
        git_config_name = self.cleaned_data.get("git_config")
        git_comment = self.cleaned_data.get("git_comment")
        content_type = self.cleaned_data.get("content_type")
        content_id = self.cleaned_data.get("content_id")
        logger.debug(f"git_config_name: {git_config_name}")
        logger.debug(f"git_comment: {git_comment}")
        logger.debug(f"content_type: {content_type}")
        logger.debug(f"content_id: {content_id}")
        logger.debug(f"user: {self.user}, type: {type(self.user)}")
        git_commit_id = create_git_commit_from_content(content_type, content_id,
                                                       git_config_name,
                                                       git_comment, self.user)

        # Returns the name of the Git Config to be used as the success message
        return git_commit_id

    def format_outbound_configs(self):
        git_configs = GitManagementConfigs(self.user, "git_config")
        outbound_configs = []
        for c in git_configs.get_git_configs():
            if c["config_type"] == "outbound":
                config_name = f'{c["name"]} (Repo: {c["repo"]}, Branch: ' \
                              f'{c["branch"]})'
                outbound_configs.append((c["name"], config_name))
        outbound_configs.insert(0, ("", "------Select a Git Config------"))
        return outbound_configs


class GitCommitMultipleForm(GitCommitForm):
    def __init__(self, *args, **kwargs):
        # super_kwargs = {"initial": kwargs.get("initial", {})}
        super(GitCommitMultipleForm, self).__init__(*args, **kwargs)
        initial = kwargs.get("initial", {})
        self.user = initial.get("user", None)

        self.content_type = initial.get("content_type", None)
        self.fields["content_id"] = forms.MultipleChoiceField(
            label=f"{self.content_type}s",
            choices=get_content_choices(self.content_type),
            widget=SelectizeMultiple,
            required=True,
            help_text=f"Select the {self.content_type}s to commit. A new commit"
                      f" will be created for each {self.content_type} selected",
        )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self):
        git_config_name = self.cleaned_data.get("git_config")
        git_comment = self.cleaned_data.get("git_comment")
        content_type = self.cleaned_data.get("content_type")
        content_ids = self.cleaned_data.get("content_id")
        logger.debug(f"content_id: {content_ids}")
        logger.debug(f"user: {self.user}")
        logger.debug(f"git_comment: {git_comment}")

        commit_ids = []
        for content_id in content_ids:
            this_git_comment = f"{git_comment} - {content_id}"
            git_commit_id = create_git_commit_from_content(content_type,
                                                           content_id,
                                                           git_config_name,
                                                           this_git_comment,
                                                           self.user)
            commit_ids.append(git_commit_id)

        # Returns the name of the Git Config to be used as the success message
        return ', '.join(commit_ids)
