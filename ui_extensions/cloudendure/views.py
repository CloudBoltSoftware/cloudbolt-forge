import time

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from extensions.views import TabExtensionDelegate, admin_extension, tab_extension
from infrastructure.models import CustomField, Server
from tabs.views import TabGroup
from utilities.decorators import dialog_view
from utilities.templatetags import helper_tags
from utilities.permissions import cbadmin_required
from cbhooks.models import CloudBoltHook

from xui.cloudendure.forms import CloudEndureConnectionForm, CloudEndureProjectSelectForm, CloudEndureProjectNameForm, CloudEndureLaunchTypeForm
from xui.cloudendure.cloudendure_admin import CloudEndureManager


class CloudEndureDelegate(TabExtensionDelegate):
    def should_display(self):
        return True


@dialog_view
@cbadmin_required
def add_cloudendure_endpoint(request):
    """
    Create credentials for CloudEndure integration into CloudBolt
    """
    action_url = reverse('add_cloudendure_endpoint')

    if request.method == 'POST':
        form = CloudEndureConnectionForm(request.POST)
        if form.is_valid():
            form.save()
            msg = "The CloudEndure credentials have been saved."
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = CloudEndureConnectionForm()

    return {
        'title': 'Add CloudEndure connection credentials',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "CloudEndure credentials",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def edit_cloudendure_endpoint(request):
    """
    Edit CloudEndure connection credentials
    """
    connection_info = CloudEndureManager().get_connection_info()

    action_url = reverse('edit_cloudendure_endpoint')
    if request.method == 'POST':
        form = CloudEndureConnectionForm(
            request.POST, instance=connection_info)
        if form.is_valid():
            form.save()
            msg = "The CloudEndure credentials have been updated"
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = CloudEndureConnectionForm(instance=connection_info)

    return {
        'title': 'Edit CloudEndure Endpoint Settings',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "CloudEndure Endpoint Settings. Supports agent install, replication and migration.",
        'submit': 'Save',
    }


@dialog_view
@cbadmin_required
def verify_cloudendure_connection(request):
    cloudendure = CloudEndureManager()

    if cloudendure.verify_connection():
        msg = format_html(
            '<p style="color: green">Successfully connected to CloudEndure</p>')
    else:
        msg = format_html(
            '<p style="color: red">Could not make a connection to CloudEndure</p>')

    return {
        'title': 'Verify connection to CloudEndure Endpoint',
        'content': msg,
        'submit': None,
        'cancel': "OK",
    }


@dialog_view
@cbadmin_required
def delete_cloudendure_endpoint(request):
    cloudendure_ci = CloudEndureManager().get_connection_info()
    if request.method == 'POST':
        cloudendure_ci.delete()
        msg = "The CloudEndure Endpoint has been deleted."
        messages.success(request, msg)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    return {
        'title': 'Remove CloudEndure Endpoint?',
        'content': 'Are you sure you want to delete CloudEndure Endpoint',
        'use_ajax': True,
        'action_url': reverse('delete_cloudendure_endpoint'),
        'submit': 'Remove'
    }


@dialog_view
@cbadmin_required
def cloudendure_machine_migration(request, project_id, machine_id):
    action_url = reverse('cloudendure_machine_migration',
                         args=[project_id, machine_id])

    if request.method == 'POST':
        cloud_endure_manager = CloudEndureManager()
        form = CloudEndureLaunchTypeForm(request.POST)
        response = cloud_endure_manager.launch_machine(
            project_id, machine_id, form.data['launch_type'])
        if response[0] == 202:
            messages.success(request, response[1])
        elif response[0] == 400:
            messages.warning(request, response[1])
        elif response[0] == 402:
            messages.warning(request, response[1])
        else:
            messages.error(request, response)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    return {
        'title': _("Migrate VM to AWS?"),
        'form': CloudEndureLaunchTypeForm(),
        'use_ajax': True,
        'action_url': action_url,
        'submit': _("Migrate"),
    }


@admin_extension(title='CloudEndure Management Integration', description='CloudBolt CloudEndure Integration')
def admin_page(request):
    cloud_endure_manager = CloudEndureManager()
    cloudendure_ci = cloud_endure_manager.get_connection_info()
    machines = cloud_endure_manager.get_all_servers()
    projects = cloud_endure_manager.get_all_projects(more_info=True)
    jobs = cloud_endure_manager.get_all_jobs()

    if machines:
        for machine in machines:
            server = Server.objects.filter(
                hostname__icontains=machine.get('name')).first()
            if server:
                machine['environment'] = server.environment.name
                machine['server_url'] = server.get_absolute_url()
                machine['ip'] = server.ip
    cloudendure_context = {

        'tabs': TabGroup(
            template_dir='cloudendure/templates',
            request=request,
            tabs=[
                (_("Dashboard"), 'dashboard', dict(
                    context={"cloudendure_ci": cloudendure_ci})),
                (_("Servers"), 'servers', dict(
                    context={'machines': machines})),
                (_("Projects"), 'projects', dict(
                    context={'projects': projects})),
                (_("Jobs"), 'jobs', dict(
                    context={'jobs': jobs}))
            ],
        )
    }
    return render(request, 'cloudendure/templates/admin_page.html', cloudendure_context)


@dialog_view()
def install_cloudendure_agent(request, server_id):
    server = Server.objects.get(id=server_id)
    cloud_endure_manager = CloudEndureManager()
    if request.method == 'GET':
        form = CloudEndureProjectSelectForm()
        return {
            'title': _("Install CloudEndure Agent on this server?"),
            'form': form,
            'use_ajax': True,
            'action_url': reverse('install_cloudendure_agent', args=[server_id]),
            'submit': _("Install"),
        }

    if request.method == 'POST':
        form = CloudEndureConnectionForm(request.POST)
        install_token = cloud_endure_manager.get_agent_installation_token(form.data['project'])
        cloud_endure_project = form.data['project']

        CustomField.objects.get_or_create(
            name='cloud_endure_project', type='STR',
            defaults={'label': 'Cloud Endure Project Name', 'description': 'Name of the project the agent of this server belongs to',
                      'show_as_attribute': True})

        try:
            install_agent_action = CloudBoltHook.objects.get(name="Install CloudEndure Agent")
        except Exception:
            cloud_endure_manager.setup_cloud_endure_install_agent_action()
            install_agent_action = CloudBoltHook.objects.get(name="Install CloudEndure Agent")

        install_job = install_agent_action.run_as_job(server=server,
                                                      install_token=install_token,
                                                      cloud_endure_project=cloud_endure_project)[0]
        messages.success(request,
                         mark_safe(f"<a href='{install_job.get_absolute_url()}'>Job {install_job.id}</a> to install agent started"))

    return HttpResponseRedirect(reverse('server_detail', args=[server_id]))


@dialog_view()
def cloudendure_machine_actions(request, server_id, action):

    if action == 'start':
        new_action = "Start", "Start cloudendure replication?"
    elif action == 'stop':
        new_action = "Stop", "Stop cloudendure replication?"
    elif action == 'pause':
        new_action = "Pause", "Pause cloudendure replication?"
    elif action == 'uninstall':
        new_action = "Uninstall", "Uninstall cloudendure agent?"
    elif action == 'migrate':
        form = CloudEndureLaunchTypeForm()
        new_action = "Migrate", "Migrate VM to AWS?"

    try:
        form = form
    except NameError:
        form = None

    if request.method == 'GET':
        return {
            'title': _(new_action[1]),
            'form': form,
            'use_ajax': True,
            'action_url': reverse('cloudendure_machine_actions', args=[server_id, action]),
            'submit': _(new_action[0]),
        }
    server = Server.objects.get(id=server_id)
    cloud_endure_manager = CloudEndureManager()
    if action == 'migrate':
        form = CloudEndureLaunchTypeForm(request.POST)
        response = cloud_endure_manager.replication_actions(
            server, action, launch_type=form.data['launch_type'])
        if response[0]:
            messages.success(request, response[1])
        else:
            messages.warning(request, response[1])
    else:
        response = cloud_endure_manager.replication_actions(server, action)
        if response[0]:
            messages.success(request, response[1])
        else:
            messages.warning(request, response[1])
    return HttpResponseRedirect(reverse('server_detail', args=[server_id]))


@tab_extension(model=Server, title='CloudEndure', delegate=CloudEndureDelegate)
def cloudendure_tab(request, obj_id):
    context = {}
    server = Server.objects.get(id=obj_id)
    cloud_endure_manager = CloudEndureManager()
    context['install_ready'] = cloud_endure_manager.check_agent_status(server)[0]
    context['server'] = server

    # check if server credentials are set
    if server.password is None:
        msg = helper_tags.alert(
            'warning', 'Agent is not installed. It can not be installed because the server password is not set.')
        context['server_credentials'] = False, msg
    else:
        context['server_credentials'] = True, "Server password is set"

    # check if the server is turned on
    if server.power_status == 'POWERON':
        context['power_on'] = True, "Server is turned on"
    else:
        msg = helper_tags.alert(
            'warning', 'Agent is not installed. It can not be installed because the server is turned off.')
        context['power_on'] = False, msg

    context['machine_actions'] = [('start', 'Start Data Replication'), ('uninstall', 'Uninstall Agent'),
                                  ('pause', 'Pause Data Replication'), ('stop', 'Stop Data Replication'), ('migrate', 'Migrate VM to AWS')]

    install_job = server.jobs.filter(job_parameters__hookparameters__hook__name='Install CloudEndure Agent').last()
    job_running = False
    if install_job and install_job.is_active():
        job_running = True
        context['job_url'] = install_job.get_absolute_url()

    context['job_running'] = job_running
    return render(request, 'cloudendure/templates/server_tab.html', context)


@dialog_view
@cbadmin_required
def create_cloudendure_project(request):
    """
    Create a cloud endure project
    """
    action_url = reverse('create_cloudendure_project')
    cloud_endure_manager = CloudEndureManager()
    if request.method == 'POST':
        form = CloudEndureProjectNameForm(request.POST)
        response = cloud_endure_manager.create_project(
            form.data['project_name'], form.data['cloud'], form.data['public_key'], form.data['private_key']
        )
        if response.status_code == 201:
            msg = "The CloudEndure project has been created."
        else:
            msg = "Project could not be created"
        messages.success(request, msg)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = CloudEndureProjectNameForm()

    return {
        'title': 'Add a CloudEndure project',
        'form': form,
        'use_ajax': True,
        'action_url': action_url,
        'top_content': "",
        'submit': 'Save',
    }
