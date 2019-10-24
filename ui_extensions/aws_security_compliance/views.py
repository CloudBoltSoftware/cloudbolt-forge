import json

from django.shortcuts import render

from extensions.views import tab_extension, TabExtensionDelegate
from infrastructure.models import CustomField
from resourcehandlers.models import ResourceHandler
from resourcehandlers.aws.models import AWSHandler
from utilities.decorators import json_view


class AWSResourceHandlerSecurityComplianceTabDelegate(TabExtensionDelegate):
    def should_display(self):
        rh: AWSHandler = self.instance
        cf_queryset = CustomField.objects.filter(
            name=f"aws_security_compliance__{rh.id}"
        )
        return cf_queryset.exists() and isinstance(self.instance.cast(), AWSHandler)


@tab_extension(
    model=ResourceHandler,
    title="Security Hub",
    delegate=AWSResourceHandlerSecurityComplianceTabDelegate,
)
def aws_handler_tab(request, obj_id):
    context = {"rh_id": obj_id}
    return render(
        request, "aws_security_compliance/templates/security_tab.html", context=context
    )


@json_view
def aws_security_compliance_json(request, rh_id):
    """
    Returns AWS Security Hub findings as JSON for a given AWS Resource Handler.
    """
    rh = AWSHandler.objects.get(id=rh_id)
    cf_queryset = CustomField.objects.filter(name=f"aws_security_compliance__{rh.id}")

    if not cf_queryset.exists():
        return []

    cf = cf_queryset.first()
    cfv = cf.customfieldvalue_set.first()
    response = json.loads(cfv.value)

    findings = []
    for finding in response:
        findings.append(
            [
                finding["Title"],
                finding["Description"],
                finding["Region"],
                finding["Severity"]["Product"],
                finding["Compliance"],
                finding["Reference"],
            ]
        )

    return {
        # unaltered from client-side value, but cast to int to avoid XSS
        # http://datatables.net/usage/server-side
        "sEcho": int(request.GET.get("sEcho", 1)),
        "iTotalRecords": 10,
        "iTotalDisplayRecords": 10,
        "aaData": findings,
    }
