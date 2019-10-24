from django import forms

from accounts.models import Group
from common.forms import C2Form, get_add_params_formfield
from infrastructure.models import CustomField


class AddDynamicGroupParameterForm(C2Form):
    """
    Form for adding Dynamic Resource Group parameters to a given Group.
    """

    group_id = forms.CharField(initial="-1", widget=forms.widgets.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "initial" in kwargs:
            group_id = kwargs["initial"]["group_id"]
        else:
            group_id = args[0]["group_id"]
        group = Group.objects.get(id=group_id)
        namespace = kwargs.get("namespace", None)

        avail_fields = []
        used_fields = set(group.custom_fields.filter(namespace=namespace))
        namespaced_fields = CustomField.objects.filter(namespace=namespace)
        for field in namespaced_fields:
            if field not in used_fields and field not in avail_fields:
                avail_fields.append(field)

        self.fields["params"] = get_add_params_formfield(avail_fields)

    def save(self):
        group_id = self.cleaned_data["group_id"]
        group = Group.objects.get(id=group_id)

        selected_params = self.cleaned_data["params"]

        added_params = []
        for param in selected_params:
            param_type, param_id = param.split("-")
            if param_type == "customfield":
                field = CustomField.objects.get(id=param_id)
                group.custom_fields.add(field)
                added_params.append(field)
            else:
                raise ValueError("Only CustomField parameters allowed.")

        return added_params
