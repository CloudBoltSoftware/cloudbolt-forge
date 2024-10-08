from __future__ import unicode_literals
from api.routers import CloudBoltDefaultRouter
from api.serializers import CustomJWTSerializer
from api.v2 import viewsets
from django.conf.urls import include, url
from rest_framework_jwt.views import ObtainJSONWebToken
router = CloudBoltDefaultRouter()
from xui.api_extension.views import set_template_creds, ResourceHandlerViewSetExtend
router.register('resource-handlers/(?P<resource_handler_id>\\d+)/set-template-creds/',
                ResourceHandlerViewSetExtend)
xui_urlpatterns = [
        url('^api/v2/resource-handlers/(?P<id>\\d+)/set-template-creds/$',
            set_template_creds, name='set_template_creds'),
]

