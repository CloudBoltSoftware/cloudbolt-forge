import json

from extensions.views import admin_extension
from tabs.views import TabGroup
from utilities.get_current_userprofile import get_current_userprofile
from utilities.permissions import cbadmin_required
from xui.git_management.forms import GitConfigForm, GitCommitForm, \
    GitCommitMultipleForm, GitTokenForm
from xui.git_management.utilities import get_all_blueprints, get_documentation,\
    get_all_orchestration_actions, get_all_server_actions, \
    get_all_xuis, get_all_recurring_jobs, format_xuis_for_template, \
    format_recurring_jobs_for_template, format_orch_actions_for_template, \
    format_server_actions_for_template, format_bps_for_template, \
    GitManagementConfigs
from django.utils.translation import ugettext as _
from utilities.decorators import dialog_view
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.contrib import messages
from django.utils.html import format_html
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


@admin_extension(
    title="Git Management",
    description="This extension allows you to export content from CloudBolt to "
                "a Git Repo")
@cbadmin_required
def git_manager(request):
    user = get_current_userprofile()
    git_config = GitManagementConfigs(user, "git_config")
    git_tokens = GitManagementConfigs(user, "git_tokens")
    config_context = {
        "git_connections": git_tokens.get_git_configs(),
        "docs": get_documentation(),
        "git_configs": git_config.get_git_configs(),
    }

    """
    The admin context for each tab is currently set up to support up to 3
    columns worth of data other than the label for each object. The payload 
    should be structured like the following. The number of items in the columns 
    list in the context class should match the number of columns in the payload. 
    content = {
        "global_id": "",
        "label": "", 
        "column_1_data": "",
        "column_2_data": "",
        "column_3_data": "",
    }         
    """
    bps = get_all_blueprints()
    bp_context = {
        "contents": format_bps_for_template(bps),
        "content_label": "Blueprints",
        "content_type": "ServiceBlueprint",
        "columns": ["Blueprint Name", "Global ID", "Resource Type"]
    }

    server_actions = get_all_server_actions()
    sa_context = {
        "contents": format_server_actions_for_template(server_actions),
        "content_label": "Server Actions",
        "content_type": "ServerAction",
        "columns": ["Server Action Name", "Global ID"]
    }

    orch_actions = get_all_orchestration_actions()
    oa_context = {
        "contents": format_orch_actions_for_template(orch_actions),
        "content_label": "Orchestration Actions",
        "content_type": "HookPointAction",
        "columns": ["Orchestration Action", "Global ID", "Hook Point"]
    }

    recurring_jobs = get_all_recurring_jobs()
    rj_context = {
        "contents": format_recurring_jobs_for_template(recurring_jobs),
        "content_label": "Recurring Jobs",
        "content_type": "RecurringJob",
        "columns": ["Recurring Job", "Global ID", "Type"]
    }

    xuis = get_all_xuis()
    xui_context = {
        "contents": format_xuis_for_template(xuis),
        "content_label": "UI Extensions",
        "content_type": "UIExtension",
        "columns": ["Orchestration Action", "Global ID", "Package"]
    }

    admin_context = {
        "tabs": TabGroup(
            template_dir="git_management/templates",
            context={},
            request=request,
            tabs=get_tabs(bp_context, sa_context, oa_context, rj_context,
                          xui_context, config_context),
        )
    }
    # logger.info(f"Admin context: {admin_context}")

    return render(
        request, "git_management/templates/admin_page.html",
        context=admin_context
    )


def get_tabs(bp_context, sa_context, oa_context, rj_context, xui_context,
             config_context):
    if not config_context["git_configs"]:
        tabs = [
            (_("Config"), "config", {"context": config_context}),
            (_("Documentation"), "docs", {"context": config_context}),
        ]
    else:
        tabs = [
            (_("Blueprints"), "content", {"context": bp_context}),
            (
                _("Server Actions"),
                "server_actions",
                {"context": sa_context}
            ),
            (
                _("Orchestration Actions"),
                "orchestration_actions",
                {"context": oa_context}
            ),
            (
                _("Recurring Jobs"),
                "recurring_jobs",
                {"context": rj_context}
            ),
            (
                _("UI Extensions"),
                "ui_extensions",
                {"context": xui_context}
            ),
            (_("Config"), "config", {"context": config_context}),
            (_("Documentation"), "docs", {"context": config_context}),
        ]
    # logger.debug(f"Tabs: {tabs}")
    return tabs



@dialog_view
@cbadmin_required
def create_git_config(request, config_type):
    user = get_current_userprofile()
    action_url = reverse("git_config_create", args=[config_type])
    initial = {}
    if request.body:
        body = request.body.decode('utf-8')
        for param in body.split('&'):
            key, value = param.split('=')
            initial[key] = value
    initial["config_type"] = config_type
    initial["user"] = user

    return submit_git_commit_form(request, initial, action_url, config_type)


@dialog_view
@cbadmin_required
def edit_git_config(request, config_type, config_name):
    user = get_current_userprofile()
    git_configs = GitManagementConfigs(user, config_type)
    initial = git_configs.get_git_config_by_name(config_name)
    initial["config_type"] = config_type
    initial["user"] = user
    action_url = reverse("git_config_edit", args=[config_type, config_name])

    return submit_git_commit_form(request, initial, action_url, config_type)


def submit_git_commit_form(request, initial, action_url, config_type):
    if request.method == "POST":
        if config_type == "git_config":
            form = GitConfigForm(request.POST, initial=initial)
        else:
            form = GitTokenForm(request.POST, initial=initial)
        if form.is_valid():
            config_name = form.save()
            msg = f"Git Config Updated: {config_name}"
            messages.success(request, msg)
            return HttpResponseRedirect(request.META["HTTP_REFERER"])
    if config_type == "git_config":
        form = GitConfigForm(initial=initial)
    else:
        form = GitTokenForm(initial=initial)

    return {
        "title": "Add Git Config",
        "form": form,
        "use_ajax": True,
        "action_url": action_url,
        "submit": "Save",
    }


@dialog_view
@cbadmin_required
def delete_git_config(request, config_type, config_name):
    user = get_current_userprofile()
    if request.method == "POST":
        # User pressed the submit button on the dialog
        git_configs = GitManagementConfigs(user, config_type)
        git_configs.delete_git_config(config_name)
        messages.success(
            request,
            format_html(
                _(f"The Git Config Info <b>{config_name}</b> was deleted.")
            ),
        )

        return HttpResponseRedirect(request.META["HTTP_REFERER"])

    else:
        content = format_html(
            _(f'<p>Delete Git Config "{config_name}"?  This action is not '
              f'reversible.</p>'),
        )
        submit = _("Delete")
        action_url = reverse("git_config_delete",
                             args=[config_type, config_name])
        logger.info(f"action_url: {action_url}")
        return {
            "title": _(f"Delete Connection Info {config_name}?"),
            "content": content,
            "use_ajax": True,
            "action_url": action_url,
            "submit": submit,
        }


@dialog_view
@cbadmin_required
def create_git_commit(request, content_type, content_id):
    user = get_current_userprofile()
    logger.debug(f"content_type: {content_type}")
    logger.debug(f"content_id: {content_id}")
    action_url = reverse("git_commit_create", args=[content_type, content_id])
    initial = {
        "content_type": content_type,
        "content_id": content_id,
        "user": user,
    }

    if request.method == "POST":
        form = GitCommitForm(request.POST, initial=initial)
        if form.is_valid():
            git_commit_id = form.save()
            msg = f"New Git Commit Created: {git_commit_id}"
            messages.success(request, msg)
            return HttpResponseRedirect(request.META["HTTP_REFERER"])
    else:
        form = GitCommitForm(initial=initial)

    return {
        "title": "Add Git Config - Commit CloudBolt Content to a Git "
                 "Repository",
        "form": form,
        "use_ajax": True,
        "action_url": action_url,
        "submit": "Save",
    }


@dialog_view
@cbadmin_required
def export_multiple(request, content_type):
    user = get_current_userprofile()
    logger.info(f"content_type: {content_type}")
    action_url = reverse("export_multiple", args=[content_type])
    initial = {
        "content_type": content_type,
        "user": user,
    }

    if request.method == "POST":
        form = GitCommitMultipleForm(request.POST, initial=initial)
        if form.is_valid():
            git_commit_id = form.save()
            msg = f"New Git Commit Created: {git_commit_id}"
            messages.success(request, msg)
            return HttpResponseRedirect(request.META["HTTP_REFERER"])
    else:
        form = GitCommitMultipleForm(initial=initial, request=request)

    return {
        "title": "Add Git Config - Commit CloudBolt Content to a Git "
                 "Repository",
        "form": form,
        "use_ajax": True,
        "action_url": action_url,
        "submit": "Save",
    }
