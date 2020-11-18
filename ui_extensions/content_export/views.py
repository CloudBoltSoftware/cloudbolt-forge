import requests

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import mark_safe

from cbhooks.models import (
    HookPointAction, RecurringActionJob, ServerAction, ResourceAction, TriggerPoint
)
from extensions.models import UIExtension, XUIIndexer
from extensions.views import admin_extension
from servicecatalog.models import ServiceBlueprint
from utilities.decorators import dialog_view
from utilities.permissions import cbadmin_required
from xui.content_export.forms import ExportContentForm


@admin_extension(title='Exportable Contents', description='All Exportable CloudBolt Contents')
@cbadmin_required
def export_content_list(request):
    """
    View for listing metadata for all exportable contents.
    """
    proto = request.META['wsgi.url_scheme']
    host = request.META['HTTP_HOST']
    
    resp = requests.get('{}://{}/api/v2/exportable-content/?version=dev'.format(proto, host), verify=False)

    exportable_contents = []
    response = resp.json()

    from api.v2.serializers import keys_hyphens_to_underscores

    if 'server-actions' in response:
        for sa in response['server-actions']:
            sa['id'] = sa['package-url'].split('/')[-2]
            sa['collections'] = 'server-actions'
            exportable_contents.append(keys_hyphens_to_underscores(sa))

    if 'orchestration-actions' in response:
        for oa in response['orchestration-actions']:
            oa['id'] = oa['package-url'].split('/')[-2]
            oa['collections'] = 'orchestration-actions'

            exportable_contents.append(keys_hyphens_to_underscores(oa))
            
    if 'ui-extension-packages' in response:
        XUIIndexer().index()
        for ui in response['ui-extension-packages']:
            id = ui['package-url'].split('/')[-1]
            ui['id'] = UIExtension.objects.get(name=id).id
            ui['collections'] = 'ui-extension-packages'
            exportable_contents.append(keys_hyphens_to_underscores(ui))
                
    if 'blueprints' in response:
        for bp in response['blueprints']:
            bp['id'] = bp['package-url'].split('/')[-2]
            bp['collections'] = 'blueprints'
            exportable_contents.append(keys_hyphens_to_underscores(bp))
    
    if 'recurring-jobs' in response:
        for job in response['recurring-jobs']:
            job['id'] = job['package-url'].split('/')[-2]
            job['collections'] = 'recurring-jobs'
            exportable_contents.append(keys_hyphens_to_underscores(job))
            
    if 'resource-actions' in response:
        for ra in response['resource-actions']:
            ra['id'] = ra['package-url'].split('/')[-2]
            ra['collections'] = 'resource-actions'
            exportable_contents.append(keys_hyphens_to_underscores(ra))

    list_context = {
        'exportable_contents': exportable_contents,
        'pagetitle': 'Exportable Contents',
    }
    return render(request, 'content_export/templates/list.html', list_context)

@dialog_view
@cbadmin_required
def export_content_edit(request, id=None, collections=''):
    """
    Edit exportable contents
    """
    if collections == 'blueprints':
        instance = ServiceBlueprint.objects.get(id=id)
    elif collections == 'resource-actions':
        instance = ResourceAction.objects.get(id=id)
    elif collections == 'server-actions':
        instance = ServerAction.objects.get(id=id)
    elif collections == 'recurring-jobs':
        instance = RecurringActionJob.objects.get(id=id)
    elif collections == 'orchestration-actions':
        instance = HookPointAction.objects.get(id=id)
    elif collections == 'ui-extension-packages':
        instance = UIExtension.objects.get(id=id)
                
    if request.method == 'POST':
        form = ExportContentForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            instance = form.save()
            msg = "Metadata details for {} have been saved.".format(instance)
            messages.success(request, msg)
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = ExportContentForm(instance=instance)

    return {
        'title': 'Edit Exportable Metadata',
        'form': form,
        'action_url': reverse('export_content_edit', args=[id, collections]),
        'use_ajax': True,
        'submit': 'Save',
        'extra_onready_js': mark_safe("$('.render_as_datepicker').datepicker({dateFormat: 'yy-mm-dd'});")
    }
