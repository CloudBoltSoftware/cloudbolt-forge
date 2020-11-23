from django.shortcuts import render

from extensions.views import tab_extension
from infrastructure.models import Server, Environment
from accounts.models import Group, UserProfile
from resourcehandlers.models import ResourceHandler
from resources.models import Resource
from servicecatalog.models import ServiceBlueprint


@tab_extension(model=Server, title='Extension on Server')
def server_tab(request, obj_id):
    return render(request, 'extension_tabs/templates/tab.html', {})


@tab_extension(model=Environment, title='Extension on Environment')
def environment_tab(request, obj_id):
    return render(request, 'extension_tabs/templates/tab.html', {})


@tab_extension(model=Group, title='Extension on Group')
def group_tab(request, obj_id):
    return render(request, 'extension_tabs/templates/tab.html', {})


@tab_extension(model=UserProfile, title='Extension on UserProfile')
def user_profile_tab(request, obj_id):
    return render(request, 'extension_tabs/templates/tab.html', {})


@tab_extension(model=ResourceHandler, title='Extension on ResourceHandler')
def resource_handler_tab(request, obj_id):
    return render(request, 'extension_tabs/templates/tab.html', {})


@tab_extension(model=Resource, title='Extension on Resource')
def resource_tab(request, obj_id):
    return render(request, 'extension_tabs/templates/tab.html', {})


@tab_extension(model=ServiceBlueprint, title='Extension on ServiceBlueprint')
def blueprint_tab(request, obj_id):
    return render(request, 'extension_tabs/templates/tab.html', {})
