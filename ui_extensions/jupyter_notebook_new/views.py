from extensions.views import admin_extension, tab_extension, TabExtensionDelegate
from django.shortcuts import render
from django.conf import settings
from utilities.views import (CBAdminRequiredMixin, GlobalPreferenceRequiredMixin)
from django.views.generic import TemplateView
from portals.models import PortalConfig

class JupyterNotebook(TabExtensionDelegate):
    def should_display(self):
        return True

@admin_extension(title='Jupyter Notebooks', description='Jupyter...')
def jupyter_notebook_view(request):
    current_domain = PortalConfig.get_current_domain(request) + ":" + settings.NOTEBOOK_PORT
    notebook_base_uri = settings.NOTEBOOK_BASE_URI if hasattr(settings, 'NOTEBOOK_BASE_URI') else current_domain
    notebook_token = settings.NOTEBOOK_TOKEN
    notebook_uri = '{}/shell/?token={}'.format(notebook_base_uri, notebook_token)
    context = {
        'notebook_uri': notebook_uri,
        'pagetitle': 'Django Notebook'
    }
    return render(request, 'jupyter_notebook/templates/django-notebook.html', context)