from django.utils.translation import ugettext as _
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from infrastructure.models import Server, CustomField

from tabs.views import TabGroup
from extensions.views import (TabExtensionDelegate, admin_extension,
                              tab_extension)

from utilities.decorators import dialog_view
from utilities.permissions import cbadmin_required
from cbhooks.models import CloudBoltHook

from xui.new_relic.forms import NewRelicConnectionForm
from xui.new_relic.new_relic_helper import NewRelicManager

@admin_extension(title='New Relic Integration', description='New Relic Integration into CloudBolt')
def admin_page(request):
    new_relic_manager = NewRelicManager()
    new_relic_ci = new_relic_manager.get_connection_info()

    new_relic_context = {
        'tabs': TabGroup(
            template_dir='new_relic/templates',
            request=request,
            tabs=[
                (_("Overview"), 'dashboard', dict(
                    context={"new_relic_ci": new_relic_ci})),
            ],
        )
    }
    return render(request, 'new_relic/templates/admin_page.html', new_relic_context)


@dialog_view
@cbadmin_required
def add_credentials(request):
    action_url = reverse('add_new_relic_credentials')
    if request.method == 'GET':
        form = NewRelicConnectionForm()
    elif request.method == 'POST':
        form = NewRelicConnectionForm(request.POST)
        if form.is_valid():
            form.save()
            msg = "The New Relic credentials have been saved."
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        msg = "Method not allowed"
        messages.error(request, msg)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    return {
        'title': 'Add New Relic Credentials',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "New Relic credentials",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def edit_new_relic_credentials(request):
    new_relic = NewRelicManager()
    credentials = new_relic.get_connection_info()

    action_url = reverse('edit_new_relic_credentials')
    if request.method == 'POST':
        form = NewRelicConnectionForm(request.POST, instance=credentials)
        if form.is_valid():
            form.save()
            msg = "The New Relic credentials have been updated."
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])

    else:
        form = NewRelicConnectionForm(instance=credentials)

    return {
        'title': 'Edit New Relic Connection Info',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "New Relic credentials",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def verify_new_relic_credentials(request):
    new_relic_manager = NewRelicManager()

    ok, message = new_relic_manager.verify_credentials()
    if ok:
        msg = format_html('<p style="color: green">Credentials for the New Relic connection info verified successfully')
    else:
        msg = format_html(f'<p style="color: red">{message}</p>')
    return {
        'title': 'Verify connection to New Relic credentials',
        'content': msg,
        'submit': None,
        'cancel': "OK",
    }


@dialog_view
@cbadmin_required
def delete_new_relic_credentials(request):
    new_relic = NewRelicManager()
    new_relic_ci = new_relic.get_connection_info()

    if request.method == 'POST':
        new_relic_ci.delete()
        msg = "The New Relic credentials have been deleted."
        messages.success(request, msg)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    return {
        'title': 'Remove New Relic Credentials?',
        'content': 'Are you sure you want to delete these New Relic credentials?',
        'use_ajax': True,
        'action_url': reverse('delete_new_relic_credentials'),
        'submit': 'Remove'
    }


# Server TAB
class NewRelicTabDelegate(TabExtensionDelegate):
    def should_display(self):
        new_relic_manager = NewRelicManager()
        return new_relic_manager.get_connection_info()


@dialog_view
def install_agent(request, server_id):
    new_relic_manager = NewRelicManager()
    if request.method == 'GET':
        content = _(
            "Are you sure you want to install New Relic Agent on this server?")
        return {
            'title': _("Install Agent?"),
            'content': content,
            'use_ajax': True,
            'action_url': reverse('install_new_relic_agent', args=[server_id]),
            'submit': _("Install"),
        }
    if request.method == 'POST':
        try:
            install_agent_action = CloudBoltHook.objects.get(name="Install New Relic Agent")
        except Exception:
            new_relic_manager.setup_new_relic_install_agent_action()
            install_agent_action = CloudBoltHook.objects.get(name="Install New Relic Agent")

        server = Server.objects.get(id=server_id)
        install_job = install_agent_action.run_as_job(server=server)[0]
        messages.success(request, mark_safe(f"<a href='{install_job.get_absolute_url()}'>Job {install_job.id}</a> to install New Relic agent "
                                            f"started"))

    return HttpResponseRedirect(request.META['HTTP_REFERER'])


@dialog_view
def uninstall_agent(request, server_id):
    if request.method == 'GET':
        content = _(
            "Are you sure you want to uninstall New Relic Agent from this server?")
        return {
            'title': _("Uninstall Agent?"),
            'content': content,
            'use_ajax': True,
            'action_url': reverse('uninstall_new_relic_agent', args=[server_id]),
            'submit': _("Uninstall"),
        }
    if request.method == 'POST':
        new_relic_manager = NewRelicManager()
        server = Server.objects.get(id=server_id)
        try:
            uninstall_agent_action = CloudBoltHook.objects.get(name="UnInstall New Relic Agent")
        except Exception:
            new_relic_manager.setup_new_relic_uninstall_agent_action()
            uninstall_agent_action = CloudBoltHook.objects.get(name="UnInstall New Relic Agent")

        uninstall_job = uninstall_agent_action.run_as_job(server=server)[0]
        messages.success(request, mark_safe(f"<a href='{uninstall_job.get_absolute_url()}'>Job {uninstall_job.id}</a> to uninstall New Relic agent "
                                            f"started"))

        return HttpResponseRedirect(request.META['HTTP_REFERER'])

def get_new_relic_actions():
    return ["Uninstall Agent"]


@tab_extension(model=Server,
               title='New Relic',
               description='New Relic Server Tab',
               delegate=NewRelicTabDelegate)
def server_tab_new_relic(request, obj_id=None):
    CustomField.objects.get_or_create(
        name='new_relic_agent_installed', type='BOOL',
        defaults={'label': 'Is New Relic Agent Installed',
                  'show_as_attribute': False})

    new_relic_manager = NewRelicManager()
    context = {}

    server = get_object_or_404(Server, pk=obj_id)
    is_agent_installed = new_relic_manager.is_agent_installed(server)
    """
    The first time this server tab shows on a server, the new_relic_agent_installed will be None.
    We can update it with the is_agent_installed variable
    """
    if server.new_relic_agent_installed is None:
        server.new_relic_agent_installed = is_agent_installed
        server.save()

    statistics = new_relic_manager.get_server_statistics(server)
    if statistics:
        processor_count = statistics[0].get('processorCount')
        total_memory = int(statistics[0].get('memoryTotalBytes')) / 1e9
        disk_size = int(statistics[0].get('diskTotalBytes')) / 1e9
        cpu_percent = [[cpu.get('timestamp'), round(float(cpu.get('cpuPercent')), 2)] for cpu in statistics]
        cpu_idle_percent = [[cpu.get('timestamp'), round(float(cpu.get('cpuIdlePercent')), 2)] for cpu in statistics]
        load_average = [[cpu.get('timestamp'), round(float(cpu.get('loadAverageFiveMinute')), 2)] for cpu in statistics]
        memory_used = [[cpu.get('timestamp'), round(int(cpu.get('memoryUsedBytes'))/1e9, 2)] for cpu in statistics]
        context.update(
            {
                'processor_count': processor_count,
                'total_memory': round(total_memory),
                'disk_size': round(disk_size),
                'cpu_percent': [{'data': cpu_percent, 'name': 'CPU Percent used ', 'color': '#153c55', 'type': 'area'}],
                'cpu_idle_percent': [{'data': cpu_idle_percent, 'name': 'CPU Idle Percentage ', 'color': '#E570EF', 'type': 'area'}],
                'load_average': [{'data': load_average, 'name': 'CPU Load Average', 'color': '#4EDEE0', 'type': 'area'}],
                'memory_used': [{'data': memory_used, 'name': 'Memory Used', 'color': '#B90454', 'type': 'area'}],
            })
    install_job = server.jobs.filter(job_parameters__hookparameters__hook__name='Install New Relic Agent').last()
    uninstall_job = server.jobs.filter(job_parameters__hookparameters__hook__name='UnInstall New Relic Agent').last()
    job_running = False
    uninstall_job_running = False
    if install_job and install_job.is_active():
            job_running = True
            context.update({'job_url': install_job.get_absolute_url()})

    if uninstall_job and uninstall_job.is_active():
        uninstall_job_running = True
        context.update({'uninstall_job_url': uninstall_job.get_absolute_url()})

    context.update({'new_relic_agent_installed': server.new_relic_agent_installed, 'uninstall_job_running': uninstall_job_running})
    context.update({'server': server, 'agent_installed': is_agent_installed,
                    'install_job_running': job_running, 'new_relic_actions': get_new_relic_actions()})
    return render(request, 'new_relic/templates/new_relic_server_tab.html', context)
