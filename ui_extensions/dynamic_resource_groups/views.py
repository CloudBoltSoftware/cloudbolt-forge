from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.html import mark_safe, format_html, escape
from django.utils.translation import ungettext, ugettext as i18n
from django.views import View

from accounts.models import Group
from extensions.views import tab_extension, TabExtensionDelegate
from infrastructure.models import Namespace
from utilities import permissions
from utilities.decorators import dialog_view

from xui.dynamic_resource_groups.forms import AddDynamicGroupParameterForm


class GenericDynamicGroupParameterView(View):
    """
    """

    form_class = AddDynamicGroupParameterForm
    template_name = None  # TODO: Can we do this with a generic template?
    namespace = None
    title = None
    action_url = None

    def get(self, request, group_id=None, *args, **kwargs):
        group = self.setup(group_id)
        form = self.form_class(initial={"group_id": group.id}, namespace=self.namespace)
        return self.common_context(group, form)

    def post(self, request, group_id=None, *args, **kwargs):
        group = self.setup(group_id)
        form = self.form_class(
            request.POST, initial={"group_id": group.id}, namespace=self.namespace
        )
        if form.is_valid():
            added_params = form.save()
            msg = format_html(
                ungettext(
                    "The parameter <b>{added_params}</b> was added to group <b>{group}</b>",
                    "The parameters <b>{added_params}</b> were added to group <b>{group}</b>",
                    len(added_params),
                ),
                added_params=escape(", ".join(map(str, added_params))),
                group=group,
            )

            messages.success(request, msg)
            return HttpResponseRedirect(reverse("group_detail", args=[group_id]))
        else:
            return self.common_context(group, form)

    @dialog_view(template_name="common/datatable_form_dialog.html")
    @permissions.cb_permission_required("group.manage_parameters")
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def setup(self, group_id=None):
        return get_object_or_404(Group, pk=group_id)

    def common_context(self, group, form):
        context = {
            "title": i18n("Add a {resource} to group '{group}'").format(
                resource=self.title, group=group
            ),
            "top_content": mark_safe(
                i18n(
                    "<p>Please select parameter(s) to add. "
                    "Parameters that are already in use are not shown.</p>"
                )
            ),
            "form": form,
            "ng_non_bindable": True,
            "form_height": 250,
            "use_ajax": True,
            "action_url": reverse(self.action_url, args=[group.id]),
            "submit": i18n("Add"),
        }

        return context


class DynamicGroupRuleView(GenericDynamicGroupParameterView):
    namespace = "Dynamic Group Rules"
    title = "Dynamic Rule"
    action_url = None


class DynamicGroupPolicyView(GenericDynamicGroupParameterView):
    namespace = "Dynamic Group Policies"
    title = "Dynamic Policy"
    action_url = None


class DynamicResourceGroupTabDelegate(TabExtensionDelegate):
    def should_display(self):
        _, _ = Namespace.objects.get_or_create(name="Dynamic Group Rules")
        _, _ = Namespace.objects.get_or_create(name="Dynamic Group Policies")
        return True


@tab_extension(model=Group, title="Rules", delegate=DynamicResourceGroupTabDelegate)
def group_dynamic_rules_tab(request, obj_id):
    group = get_object_or_404(Group, pk=obj_id)
    params = group.custom_fields.filter(namespace__name="Dynamic Group Rules")
    context = {
        "group_or_env": group,
        "dynamic_resource_str": "rule",
        "params": params,
        "group_or_env_str": "group",
    }

    return render(
        request, "dynamic_resource_groups/templates/rules_tab.html", context=context
    )


@tab_extension(model=Group, title="Policies", delegate=DynamicResourceGroupTabDelegate)
def group_dynamic_policies_tab(request, obj_id):
    pass
