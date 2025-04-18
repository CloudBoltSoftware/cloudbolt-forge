import json
import logging
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from extensions.views import admin_extension
from utilities.permissions import cbadmin_required
from accounts.models import Group, GroupType
from resourcehandlers.azure_arm.models import AzureARMHandler

from .azure_api import get_access_token, fetch_all_groups, get_group_by_id
from .utils import get_cmp_group_map, get_unmatched_cmp_groups

logger = logging.getLogger(__name__)


@admin_extension(
    title="Azure AD Groups V2",
    description="View Azure AD Groups from a selected Azure Resource Handler and map them to CMP Groups"
)
@cbadmin_required
def ad_group_list(request):
    selected_rh_id = request.POST.get("resource_handler")
    azure_groups = []
    error = None
    selected_rh_id_int = None

    all_rhs = AzureARMHandler.objects.all().order_by("name")
    group_types = GroupType.objects.all().order_by("group_type")
    parent_groups = Group.objects.all().order_by("name")

    if selected_rh_id:
        try:
            selected_rh_id_int = int(selected_rh_id)
            rh = AzureARMHandler.objects.get(id=selected_rh_id_int)
            token = get_access_token(rh.client_id, rh.secret, rh.azure_tenant_id)
            azure_groups = fetch_all_groups(token)
        except Exception as e:
            error = str(e)
            logger.exception("Failed to retrieve Azure AD groups")

    cmp_groups = get_cmp_group_map()
    groups = []

    for g in azure_groups:
        g["cmp_group"] = cmp_groups.get(g.get("displayName"))
        groups.append(g)

    unmatched_cmp_groups = get_unmatched_cmp_groups(cmp_groups, azure_groups)

    return render(request, "azure_ad_group_import/templates/tab-groups.html", {
        "groups": groups,
        "cmp_only_groups": unmatched_cmp_groups,
        "error": error,
        "resource_handlers": all_rhs,
        "selected_rh_id": selected_rh_id_int,
        "group_types": group_types,
        "parent_groups": parent_groups,
    })


@cbadmin_required
def group_detail(request, group_id):
    try:
        rh = AzureARMHandler.objects.first()
        if not rh:
            raise Exception("No Azure Resource Handler configured.")

        token = get_access_token(rh.client_id, rh.secret, rh.azure_tenant_id)
        group_data = json.dumps(get_group_by_id(group_id, token), indent=2)

        return render(request, "azure_ad_group_import/templates/group-detail.html", {
            "group": group_data
        })

    except Exception as e:
        logger.exception("Failed to fetch group details")
        return render(request, "azure_ad_group_import/templates/group-detail.html", {
            "error": str(e),
            "group": {}
        })


@csrf_exempt
@cbadmin_required
def create_cmp_group(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name")
            group_type_id = data.get("group_type_id")
            parent_group_id = data.get("parent_group_id")

            if not name:
                return JsonResponse({"error": "Missing group name"}, status=400)

            group_type = GroupType.objects.get(id=group_type_id)
            parent_group = Group.objects.get(id=parent_group_id) if parent_group_id else None

            user = request.user
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            description = f"Imported from Azure AD on {timestamp} by {user}"

            group, created = Group.objects.get_or_create(
                name=name,
                defaults={
                    "type": group_type,
                    "parent": parent_group,
                    "description": description
                }
            )

            return JsonResponse({"status": "created" if created else "exists"})

        except Exception as e:
            logger.exception("Failed to create CMP group")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid method"}, status=405)
