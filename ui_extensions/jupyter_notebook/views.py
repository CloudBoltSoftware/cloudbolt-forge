import subprocess
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView
from c2_wrapper import create_hook
from cbhooks.models import CloudBoltHook
from extensions.views import admin_extension, tab_extension, TabExtensionDelegate
from portals.models import PortalConfig
from utilities.decorators import dialog_view
from utilities.templatetags import helper_tags
from utilities.views import redirect_to_referrer
from utilities.views import (
    CBAdminRequiredMixin, GlobalPreferenceRequiredMixin)


class JupyterNotebook(TabExtensionDelegate):
    def should_display(self):
        return True


@admin_extension(title='Jupyter Notebooks', description='Jupyter...')
def jupyter_notebook_view(request):
    current_domain = PortalConfig.get_current_domain(
        request) + ":" + settings.NOTEBOOK_PORT
    notebook_base_uri = settings.NOTEBOOK_BASE_URI if hasattr(
        settings, 'NOTEBOOK_BASE_URI') else current_domain
    notebook_token = settings.NOTEBOOK_TOKEN
    notebook_uri = '{}/shell/?token={}'.format(
        notebook_base_uri, notebook_token)
    jupyterd_status = subprocess.call(["service", "jupyterd", "status"])
    if jupyterd_status == 0:
        context = {
            'jupyter_not_running': "Jupyterd is not running.",
            'pagetitle': 'Django Notebook'
        }
        return render(request, 'jupyter_notebook/templates/django-notebook.html', context)
    elif jupyterd_status == 1:
        context = {
            'notebook_uri': notebook_uri,
            'pagetitle': 'Django Notebook'
        }
        return render(request, 'jupyter_notebook/templates/django-notebook.html', context)


@dialog_view
def restart_jupyterd(request):
    """
    View for launching a job to restart JUpyterd. 
    GET: open a dialog to run or cancel
    POST: runs job.
    """
    if request.method == 'POST':
        hook = CloudBoltHook.objects.get(name="Start Jupyterd notebook Action")
        job = hook.run_as_job()[0]
        msg = (
            "Job {} has been created to restart Jupyterd".format(
                helper_tags.render_simple_link(job)))
        messages.info(request, msg)
        return HttpResponseRedirect('/notebook')
    else:
        setup_jupyter_notebook()
        content = (
            'Restart Jupyterd?')
        action_url = reverse(
            'restart_jupyterd')

        return {
            'title': 'Confirm Jupyterd Restart',
            'content': content,
            'use_ajax': True,
            'action_url': action_url,
            'submit': 'Restart',
        }


def setup_jupyter_notebook():
    jupyter_notebook_hook = {
        'name': "Start Jupyterd notebook Action",
        'description': ("Startd the Jupyterd daemon"),
        'hook_point': None,
        'module': '/var/opt/cloudbolt/proserv/xui/jupyter_notebook/start_jupyterd.py',
    }
    create_hook(**jupyter_notebook_hook)
