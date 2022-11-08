import json
import os
from os import path

from accounts.models import Group
from cbhooks.models import OrchestrationHook
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.middleware.csrf import get_token
from django.template import loader
from extensions.views import CustomFormExtensionDelegate, custom_form_extension
from servicecatalog.models import ServiceBlueprint
from utilities.decorators import json_view
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)
XUI_PATH = path.dirname(path.abspath(__file__))

class FormDelegate(CustomFormExtensionDelegate):
    """
    Define the logic for when the custom form should be displayed.

    If a Custom Field (parameter) title "custom_form" is present, the form will be rendered.

    """
    def should_display(self):
        bp = self.instance
        try: 
            cfvs = bp.get_cf_values_as_dict()
            if cfvs['custom_form']:
                return True
        except:
            return False

    def get_form_url(self):
        return f"/custom_form/{self.instance.id}/"


@custom_form_extension(delegate=FormDelegate)
@json_view
def get_custom_form(request, blueprint_id):
    """
    Implement the custom form for the blueprint.

    Provides permission checking on the blueprint and the group.

    Generates the necessary csrf token and the web hook url.
    """
    blueprint = ServiceBlueprint.objects.get(id=blueprint_id)
    profile = request.get_user_profile()

    if not blueprint.can_order(profile):
        raise PermissionDenied(
            ("Your account does not have permission to view this item.")
        )
    group_id = request.GET.get("group_id", None)
    if not group_id:
        group_id = Group.objects_for_profile(profile).first().id
    csrf_token_value = get_token(request)

    context = {
        "group_id": group_id,
        "csrf_token_value": csrf_token_value,
        "blueprint_id": blueprint.global_id,
        "file_names": get_file_names(),
    }
    content = loader.render_to_string(
        f'{XUI_PATH}/templates/form.html',
        context=context)
    return {'content': content}

@json_view
def get_custom_form_from_file(request):
    """
    Get the JSON representation of the form from a file.
    """
    try:
        file_name = request.POST.get("file_name", None)
        if file_name:
            file_path = f'{XUI_PATH}/forms/{file_name}'
            with open(file_path) as f:
                survey_json = json.load(f)
            context = {
                "survey_json": survey_json,
            }
            return context
        else:
            context = {
                "file_names": get_file_names(),
            }
        return context
    except Exception as e:
        raise e



def get_file_names():
    """ Get the list of files in the forms directory """
    file_path = f'{XUI_PATH}/forms/'
    return [f.split(".")[0] for f in os.listdir(file_path)]


@json_view
def blueprint_deploy(request):
    """
    Accept POST request from the custom form and deploy the blueprint.
    
    Passes the parameters into a pre-defined plugin, specified by name.
    """
    if request.method == "POST":
        plugin = OrchestrationHook.objects.get(name="custom_form_starter")
        job = plugin.run_as_job(parameters=request.POST, owner=request.get_user_profile())
        return {"redirectURL": f"http://0.0.0.0:8001/jobs/{job[0].id}/"}
    return {"error": "Only method supported: 'POST'"}


@json_view
def get_form_from_file(request):
    """
    Retrive a JSON file and return the contents to be processed by the
    form builder. 
    """
    try:
        file_name = request.POST.get("file_name", None)
        file_path = f'{XUI_PATH}/forms/{file_name}'
        with open(file_path) as f:
            survey_json = json.load(f)
        context = {
            "survey_json": survey_json,
        }
        return context
    except Exception as e:
        error_message = e.args[0]
        return {"status": False, "message": error_message}


