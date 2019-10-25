from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.views import View

from accounts.models import Group
from extensions.views import tab_extension, TabExtensionDelegate
from infrastructure.models import Namespace, CustomField

from xui.dynamic_resource_groups.forms import EditDynamicGroupRuleForm


class EditDynamicGroupRuleView(View):
    """
    """

    form_class = EditDynamicGroupRuleForm

    def get(self, request, group_id=None, field_id=None, *args, **kwargs):
        group, field = self.setup(request, group_id, field_id)
        form = self.form_class(group=group, field=field)
        return self.common_context(request, group, field, form)

    def post(self, request, group_id=None, field_id=None, *args, **kwargs):
        group, field = self.setup(request, group_id, field_id)
        form = self.form_class(request.POST, group=group, field=field)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("group_detail", args=[group_id]))
        else:
            return self.common_context(request, group, field, form)

    def setup(self, request, group_id=None, field_id=None):
        group = get_object_or_404(Group, pk=group_id)
        field = get_object_or_404(CustomField, pk=field_id)
        return group, field

    def common_context(self, request, group, field, form):
        return render(
            request,
            "parameters/edit_param_value_dialog.html",
            {
                "title": _('Edit Dynamic Rule on Group "{group}"').format(group=group),
                "form": form,
                "group": group,
                "field": field,
                "action_url": reverse(
                    "dynamic_group_edit_rule", args=[group.id, field.id]
                ),
                "submit": _("Save"),
            },
        )


class DynamicResourceGroupTabDelegate(TabExtensionDelegate):
    def should_display(self):
        # Should we check @permissions.cb_permission_required("group.manage_parameters")
        # here?
        rule_namespace, _ = Namespace.objects.get_or_create(name="Dynamic Group Rules")
        _, _ = Namespace.objects.get_or_create(name="Dynamic Group Policies")
        _ = _create_rules_custom_field(rule_namespace)

        return True


def _create_rules_custom_field(namespace):
    """
    """
    rule_custom_field, _ = CustomField.objects.get_or_create(name="tags_to_include")
    rule_custom_field.label = "Tags to Include"
    rule_custom_field.namespace = namespace
    rule_custom_field.type = "CODE"
    rule_custom_field.save()
    return


@tab_extension(model=Group, title="Rules", delegate=DynamicResourceGroupTabDelegate)
def group_dynamic_rules_tab(request, obj_id):
    group = get_object_or_404(Group, pk=obj_id)
    _ = _add_dynamic_rules_to_group(group)
    params = _get_dynamic_rules(group)
    context = {
        "group": group,
        "dynamic_resource_str": "rule",
        "params": params,
        "group_or_env_str": "group",
    }

    return render(
        request, "dynamic_resource_groups/templates/rules-tab.html", context=context
    )


def _add_dynamic_rules_to_group(group):
    custom_field = CustomField.objects.get(
        name="tags_to_include", namespace__name="Dynamic Group Rules"
    )
    group.custom_fields.add(custom_field)
    group.save()
    return


def _get_dynamic_rules(group):
    """
    Return list of (CF, display value) tuples for all Dynamic Rule CFs
    associated with this Group. List is sorted by CF name.
    """
    # group_cfvs = group.custom_field_options.filter(
    #     field__namespace__name="Dynamic Group Rules"
    # ).order_by('field__name').distinct()
    group_cfs = (
        group.custom_fields.filter(namespace__name="Dynamic Group Rules")
        .order_by("name")
        .distinct()
    )

    return [
        (cf, group.get_display_value_for_custom_field(cf_object=cf)) for cf in group_cfs
    ]


@tab_extension(model=Group, title="Policies", delegate=DynamicResourceGroupTabDelegate)
def group_dynamic_policies_tab(request, obj_id):
    pass
