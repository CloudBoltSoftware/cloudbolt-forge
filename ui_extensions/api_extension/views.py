from __future__ import unicode_literals
from datetime import datetime
from django.db.models import Q
from django.utils.translation import ugettext as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from api.decorators import link
from api.exceptions import APIException
from rest_framework.decorators import api_view
from api.viewsets import CloudBoltViewSet, ImportExportViewsetMixin, action_return, dict_return
from api.v2.viewsets import ResourceHandlerViewSet, SetEnabledMixin
from resourcehandlers.models import ResourceHandler
from resources.models import Resource
from utilities.logger import ThreadLogger
from resourcehandlers.serializers import ResourceHandlerSerializer
from api.v2.pagination import ResourceHandlerPagination
from extensions.views import admin_extension
from django.shortcuts import render
from utilities.permissions import cbadmin_required
logger = ThreadLogger(__name__)


@admin_extension(title="API Extension")
def apiextensions(request, *args, **kwargs):
    return render(request, "api_extension/templates/api.html")


class ResourceHandlerViewSetExtend(ResourceHandlerViewSet, SetEnabledMixin, ImportExportViewsetMixin):
    def __init__(self, id, request):
        self.id = id
        self.request = request
    model = ResourceHandler
    serializer_class = ResourceHandlerSerializer
    pagination_class = ResourceHandlerPagination

    #@cbadmin_required
    @link(methods=['post'])
    def set_template_creds(self, *args, **kwargs):
        """
        Endpoint for Setting Credentials on Template with an option sshkey, to
        the RH.

        Single POST:
            {
                "template": "{{template_name}}",
                "user-name": "{{user_name}}",
                "password": "{{password}}",
                "ssh-key":"{{ssh_key}}"
            }

        Array POST:
            [{
                "template": "{{template_name}}",
                "user-name": "{{user_name}}",
                "password": "{{password}}",
                "ssh-key":"{{ssh_key}}"
            },
            {
                "template": "{{template_name}}",
            }]
        """
        resp = {}
        rh = ResourceHandler.objects.get(id=self.id)
        handler = rh.cast()
        if not handler.can_import_templates_api:
            raise APIException(_('Bad Request: Invalid Resource Handler'),
                code=400,
                details=_('API endpoint is not currently supported for this resource handler.'))

        profile = self.request.get_user_profile()
        if not profile.is_cbadmin:
            raise PermissionDenied(
                _("This action requires 'CB Admin' or 'Super Admin' privileges."))

        combined_requests = self._verify_api_template_creds_json(self.request.data)
        all_reqs = []
        for req_template, req_username, req_password, req_sshkey in combined_requests:
            logger.info(f"Attempting to set credentials on {req_template}")
            template = handler.os_build_attributes.filter(
                template_name=req_template).first().cast()
            logger.info(template)
            logger.info(dir(template))
            if template:
                template.password = req_password
                template.username = req_username
                template.save()
                handler.save()
                message = f"Template Credentials updated for {template}."
                resp['message'] = message
                resp['status_code'] = 200
                all_reqs.append(resp)
            else:
                message = f"Template {req_template} Not Found"
                resp['message'] = message
                resp['status_code'] = 400
                all_reqs.append(resp)
        overall = {}
        overall['message'] = f"Template Credentials updated for {template}."
        overall['status_code'] = 200
        for resp in all_reqs:
            if resp['status_code'] != 200:
                overall['status_code'] = resp['status_code']
                overall['message'] = resp['message']
        return Response(overall, status=overall['status_code'])

    def _verify_api_template_creds_json(self, request_data):
        """
        Validate incoming POST request data and create pairs of templates and os_builds
        to import to a specific resource handler.
        """
        logger.info("Confirming Payload for set-template-creds")
        if not isinstance(request_data, list):
            request_data = [
                request_data]
        requested_templates, requested_usernames, requested_passwords, requested_sshkeys = [], [], [], []
        for template in request_data:
            requested_template = template.get('template', None)
            requested_username = template.get('user-name', None)
            requested_password = template.get('password', None)
            requested_sshkey = template.get('ssh-key', None)
            if requested_sshkey == '':
                requested_sshkey = None
            logger.info(requested_sshkey)
            if requested_template in requested_templates:
                raise APIException(_('Bad Request: Duplicate Names'),
                    code=400,
                    details=_("'template' and 'os_build' must be assigned unique values for each entry in POST request"))
            else:
                requested_templates.append(requested_template)
                requested_usernames.append(requested_username)
                requested_passwords.append(requested_password)
                requested_sshkeys.append(requested_sshkey)
        return zip(requested_templates, requested_usernames, requested_passwords, requested_sshkeys)


@api_view(['POST'])
def set_template_creds(request, id, *args, **kwargs):
    rh = ResourceHandlerViewSetExtend(id=id, request=request)
    resp = rh.set_template_creds()
    return resp


#Sample Payloads
#{
#    "template": "templatename",
#    "user-name": "myuser",
#    "password": "mytemplatepassword"
#}
#

