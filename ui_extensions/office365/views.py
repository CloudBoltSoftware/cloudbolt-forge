from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.shortcuts import render
from django.utils.html import format_html

from utilities.decorators import dialog_view
from utilities.permissions import cbadmin_required
from extensions.views import (TabExtensionDelegate, admin_extension,
                              tab_extension)
from tabs.views import TabGroup

from xui.office365.forms import Office365ConnectionForm
from xui.office365.office365_helper import Office365Manager


@dialog_view
@cbadmin_required
def add_credentials(request):
    action_url = reverse('add_office_credentials')
    if request.method == 'GET':
        form = Office365ConnectionForm()
    elif request.method == 'POST':
        form = Office365ConnectionForm(request.POST)
        if form.is_valid():
            form.save()
            msg = "The Office365 credentials have been saved."
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        msg = "Method not allowed"
        messages.error(request, msg)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    return {
        'title': 'Add Office365 Credentials',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "Office365 credentials",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def edit_credentials(request):
    credentials = Office365Manager.get_connection_info()
    action_url = reverse('edit_office_credentials')
    if request.method == 'POST':
        form = Office365ConnectionForm(request.POST, instance=credentials)
        if form.is_valid():
            form.save()
            msg = "The Office365 credentials have been updated."
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = Office365ConnectionForm(initial={
            'ip': credentials.ip, 'headers': credentials.headers, 'protocol': credentials.protocol})

    return {
        'title': 'Edit Office365 connection credentials',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "Office365 credentials",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def delete_credentials(request):
    office365_ci = Office365Manager.get_connection_info()
    action_url = reverse('delete_office_credentials')
    if request.method == 'POST':
        office365_ci.delete()
        msg = "The Office365 credentials have been deleted."
        messages.success(request, msg)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    return {
        'title': 'Remove Office365 Credentials?',
        'content': 'Are you sure you want to delete these Office365 credentials?',
        'use_ajax': True,
        'action_url': action_url,
        'submit': 'Remove'
    }


@dialog_view
@cbadmin_required
def verify_office_credentials(request):
    office_manager = Office365Manager()
    ci = office_manager.get_connection_info()

    ok, message = office_manager.verify_credentials(ci.protocol, ci.ip, ci.port, ci.headers)
    if ok:
        msg = format_html('<p style="color: green">Credentials for the Office365 connection info verified successfully')
    else:
        msg = format_html(f'<p style="color: red">{message}</p>')
    return {
        'title': 'Verify connection to Office365 credentials',
        'content': msg,
        'submit': None,
        'cancel': "OK",
    }


@admin_extension(title='Office365 Integration', description='Office365 Integration into CloudBolt')
def admin_page(request):
    office_context = {

        'tabs': TabGroup(
            template_dir='office365/templates',
            request=request,
            tabs=[
                (_("Dashboard"), 'dashboard', dict(
                    context={"office_ci": Office365Manager.get_connection_info()})),
            ],
        )
    }
    return render(request, 'office365/templates/admin_page.html', office_context)
