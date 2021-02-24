from django.shortcuts import render

from accounts.models import Group
from extensions.views import admin_extension, tab_extension, \
    TabExtensionDelegate
from infrastructure.models import Server
from resourcehandlers.aws.models import AWSHandler
from resourcehandlers.azure_arm.models import AzureARMHandler
from resourcehandlers.models import ResourceHandler
from utilities.decorators import dialog_view, json_view
from utilities.middleware import login_not_required
from utilities.permissions import cbadmin_required


class ServerTabDelegate(TabExtensionDelegate):

    def should_display(self):
        return True

        # server: Server = self.instance
        # rh = server.environment.resource_handler.cast()
        # return isinstance(rh, AWSHandler) or isinstance(rh, AzureARMHandler)


class ResourceHandlerTabDelegate(TabExtensionDelegate):

    def should_display(self):
        return True

        # rh: ResourceHandler = self.instance
        # rh = rh.cast()
        # return isinstance(rh, AWSHandler) or isinstance(rh, AzureARMHandler)


class GroupTabDelegate(TabExtensionDelegate):

    def should_display(self):
        return True


@admin_extension(title="Kumolus Integration Kit",
                 description="Kumolus Integration Kit for Cloudbolt CMP")
def display_admin(request, **kwargs):
    return render(request, 'kumo_integration_kit/templates/admin.html',
                  context={'docstring': 'Kumolus integration setup'})


@tab_extension(model=Server,
               title="Optimization",
               description="Server cost visibility and optimization",
               delegate=ServerTabDelegate)
def display_server_tab(request, server):
    return render(request, 'kumo_integration_kit/templates/server.html')


@tab_extension(model=Group,
               title="Optimization",
               description='Group cost visibility and optimization',
               delegate=GroupTabDelegate)
def display_group_tab(request, group):
    return render(request, 'kumo_integration_kit/templates/group.html')


@tab_extension(model=ResourceHandler,
               title="Costs",
               description='Resource Handler cost visibility and optimization',
               delegate=ResourceHandlerTabDelegate)
def display_group_tab(request, resource_handler):
    return render(
        request,
        'kumo_integration_kit/templates/resource_handler.html')
