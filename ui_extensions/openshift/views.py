from django.utils.translation import ugettext as _
from django.shortcuts import render
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.html import format_html

from extensions.views import admin_extension, tab_extension, TabExtensionDelegate
from tabs.views import TabGroup

from utilities.decorators import dialog_view
from utilities.permissions import cbadmin_required
from utilities.models import ConnectionInfo

from xui.openshift.forms import OpenShiftConectionForm
from xui.openshift.openshiftmanager import OpenshiftManager


@admin_extension(title='OpenShift Management Integration', description='For openshift clusters management.')
def admin_page(request):
    openshift = OpenshiftManager()
    openshift_ci = openshift.get_connection_info()

    openshift_context = {

        'tabs': TabGroup(
            template_dir='openshift/templates',
            context={'openshift_ci': openshift_ci},
            request=request,
            tabs=[
                # First tab uses template 'groups/tabs/tab-main.html'
                # (_("Configuration"), 'configuration', {}),
                # Tab 2 is conditionally-shown in this slot and
                # uses template 'groups/tabs/tab-related-items.html'
                (_("Dashboard"), 'dashboard', dict(context={})),
            ],
        )
    }
    return render(request, 'openshift/templates/admin_page.html', openshift_context)

@dialog_view
@cbadmin_required
def add_credentials(request):
    """
    Create credentials for SolarWinds integration.
    """
    action_url = reverse('add_openshift_credentials')
    if request.method == 'POST':
        form = OpenShiftConectionForm(request.POST)
        if form.is_valid():
            form.save()
            msg = "The SolarWinds credentials have been saved."
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = OpenShiftConectionForm()

    return {
        'title': 'Add Openshift Connection Info',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "Openshift credentials",
        'submit': 'Save',
    }

@dialog_view
@cbadmin_required
def verify_credentials(request):
    openshift_manager = OpenshiftManager()
    openshift_ci = openshift_manager.get_connection_info()
    openshift = OpenshiftManager(openshift_ci.ip, openshift_manager.get_token())
    response = openshift.verify_rest_credentials()

    if response:
        msg = format_html('Successfully connected to Openshift')
    else:
        msg = format_html(
            'Could not make a connection to Openshift with this token')

    return {
        'title': 'Verify connection to Openshift credentials',
        'content': msg,
        'submit': None,
        'cancel': "OK",
    }

@dialog_view
@cbadmin_required
def edit_openshift_credentials(request):
    openshiftmanager = OpenshiftManager()
    openshift_credentials = openshiftmanager.get_connection_info()

    action_url = reverse('edit_openshift_credentials')
    if request.method == 'POST':
        form = OpenShiftConectionForm(request.POST, instance=openshift_credentials)
        if form.is_valid():
            form.save()
            msg = "The Openshift details have been updated."
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])

    else:
        form = OpenShiftConectionForm(instance=openshift_credentials)

    return {
        'title': 'Edit Openshift Connection Info',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "Openshift credentials",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def delete_credentials(request):
    openshift = OpenshiftManager()
    openshift_ci = openshift.get_connection_info()
    if request.method == 'POST':
        openshift_ci.delete()
        msg = "The Openshift credentials have been deleted."
        messages.success(request, msg)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    return {
        'title': 'Remove Openshift Credentials?',
        'content': 'Are you sure you want to delete these Openshift credentials?',
        'use_ajax': True,
        'action_url': reverse('delete_openshift_credentials'),
        'submit': 'Remove'
    }
