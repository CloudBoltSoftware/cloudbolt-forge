from django.conf.urls import url
from xui.aws_security_compliance.views import aws_security_compliance_json

xui_urlpatterns = [
    url(
        r"^aws_security_compliance/(?P<rh_id>\d+)/$",
        aws_security_compliance_json,
        name="aws_security_compliance_json",
    )
]
