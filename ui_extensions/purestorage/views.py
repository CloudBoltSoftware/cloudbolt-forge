from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import ugettext as _
from utilities.models import ConnectionInfo
import base64
import requests
import json

from extensions.views import admin_extension, tab_extension, TabExtensionDelegate
from infrastructure.models import Server
from orders.models import CustomFieldValue
from utilities.decorators import dialog_view
from django.shortcuts import render

from infrastructure.models import Server
from common.methods import generate_string_from_template
from infrastructure.models import CustomField

from .forms import ClientForm
from .purestorage_manager import PureStorageManager

class PureStorageDelegate(TabExtensionDelegate):
    def should_display(self):
        return True

@tab_extension(model=Server, title='Pure Storage', delegate=PureStorageDelegate)
def dialog_sample_tab(request, obj_id):
    server = Server.objects.get(id=obj_id)
    pure_storage=PureStorageManager()

    return render(request, 'purestorage/templates/sample_tab.html', dict(
        server=server, volumes=pure_storage.get_volumes(),snapshots=pure_storage.get_snapshots()
))