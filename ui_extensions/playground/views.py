from django.shortcuts import render

from extensions.views import admin_extension, tab_extension, \
    TabExtensionDelegate, dashboard_extension
from resourcehandlers.models import ResourceHandler
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


class ResourceHandlerTabDelegate(TabExtensionDelegate):
    # We want this tab to display for all resource handlers, so we return
    # True regardless of what Resource Handler is being displayed.
    # If the goal is to target a specific Resource
    # Handler, say AWSHandler, the body of this method would be:
    # return if isinstance(self.instance.cast(), AWSHandler) else False
    def should_display(self):
        return True


@admin_extension(
    title="Playground Admin",
    description="Entrypoint for Playground Admin Extension")
def show_admin_extension(request, **kwargs):
    return render(request, template_name='playground/templates/admin.html')


@tab_extension(
    model=ResourceHandler,
    title="Playground__",
    description="Entrypoint for Playground Resource Handler Tab Extension",
    delegate=ResourceHandlerTabDelegate
)
def show_rh_tab_extension(request, model_id, **kwargs):
    return render(request, template_name='playground/templates/tab.html')


@dashboard_extension(
    title="Playground_",
    description='Playground widget')
def show_playground_widget(request):
    return render(request, template_name='playground/templates/widget.html')
