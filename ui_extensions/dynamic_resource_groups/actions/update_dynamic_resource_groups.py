"""
Update Dynamic Resource Groups (DRG)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

[description]
"""

from accounts.models import Group
from infrastructure.models import CustomField, Namespace, Server
from jobs.models import Job
from orders.models import CustomFieldValue
from utilities.events import add_server_event


def __test():
    """
    for copy/pasting into shell_plus
    """
    group, _ = Group.objects.get_or_create(name="Sync Group")
    namespace, _ = Namespace.objects.get_or_create(name="Dynamic Resource Group")
    cf, _ = CustomField.objects.get_or_create(
        name="tags_to_include",
        label="Tags to Include (DRG)",
        namespace=namespace,
        type="STR",
    )
    cfv, _ = CustomFieldValue.objects.get_or_create(field=cf, value="production")
    cf.customfieldvalue_set.add(cfv)
    group.custom_fields.add(cf)

    job = Job.objects.get(id=64)
    server = Server.objects.get(hostname="gab-01")
    cf = group.custom_fields.filter(namespace__name="Dynamic Resource Group")

    return job, server, cf, group


###############################################################################
###############################################################################


def fetch_servers_and_groups(job):
    """
    Return relevant Servers and Groups for this plugin.

    Returns:
        Tuple[QuerySet[Server], QuerySet[Group]]
    """
    servers = _get_servers_from_job(job)
    groups = _filter_groups()
    return servers, groups


def _get_servers_from_job(job):
    """
    Returns QuerySet of servers retrieved by Sync VMs job.

    Returns:
        QuerySet[Server]
    """
    jp = job.job_parameters.cast()
    return Server.objects.filter(
        resource_handler__in=jp.resource_handlers.all()
    ).exclude(status="HISTORICAL")


def _filter_groups():
    """
    Returns Groups with relevant DRG information (e.g. 'tags_to_include'
    CustomField).

    Returns:
        QuerySet[Group]
    """
    dynamic_resource_cfs = CustomField.objects.filter(
        namespace__name="Dynamic Resource Group"
    )
    return Group.objects.filter(custom_fields__in=dynamic_resource_cfs)


def update_server(server, group, job):
    """
    Wrapper method that performs Dynamic Resource Grouping logic.
    """
    _ = _assign_server(server, group, job)
    _ = _apply_policy_to_server(server, group)
    return


def _assign_server(server, group, job):
    """
    Reassigns servers to the appropriate DRG.
    """
    _ = _remove_server_from_group(server, group)
    _ = _add_server_to_group(server, group)

    return


def _remove_server_from_group(server, job):
    """
    Converts a server's group to "Unassigned" if its group was most recently
    assigned by this plug-in.
    """
    history_events = server.serverhistory_set.filter(
        event_type="MODIFICATION"
    ).order_by("-id")
    for event in history_events:
        # TODO: Getting group information in a convoluted way, reconsider how
        # this message parsing and setting works.
        if "update_dynamic_resource_groups" in event.event_message:
            assigned_group_id = event.event_message.split(". Group ID: ")[-1]
            last_assigned_group = Group.objects.get(id=assigned_group_id)

            if server.group == last_assigned_group and event.job != job:
                server.group = Group.objects.get(name="Unassigned")
                server.save()

            # Only consider the last Group change by this action.
            break
    return


def _add_server_to_group(server, group, job):
    """
    Assigns a group to a DRG, as appropriate.
    """
    if server.group.name != "Unassigned":
        return

    server_tags = set(_get_server_details(server).tags.values())
    group_tags = set(_get_group_values(group))
    common_tags = server_tags & group_tags

    if not common_tags:
        return

    # Assign server to group
    server.group = group
    server.save()

    # Add history event
    message = (
        f"Server added to Dynamic Resource Group '{group}' by "
        f"update_dynamic_resource_groups Action. Group ID: {group.id}"
    )

    add_server_event("MODIFICATION", server, message, job=job)

    return


def _get_server_details(server):
    """
    Return dictionary of technology-specific details for a server, including
    Tags and other potentially relevant items.

    Returns:
        dict
    """
    rh = server.get_resource_handler()
    if not rh:
        return {}
    return rh.tech_specific_server_details(server)


def _get_group_values(group):
    """
    Return list of relevant CFV values associated with the group.
    """
    values: list = []
    cfs = group.custom_fields.filter(
        namespace__name="Dynamic Resource Group"
    ).prefetch_related("customfieldvalue_set")
    for cf in cfs:
        values += [cfv.value for cfv in cf.customfieldvalue_set.all()]

    return values


def _apply_policy_to_server(server, group):
    if server.group != group:
        return

    policies = _get_dynamic_resource_group_policies(group)
    raise NotImplementedError


def _get_dynamic_resource_group_policies(group):
    raise NotImplementedError


def run(job, *args, **kargs):
    servers, groups = fetch_servers_and_groups(job)
    for server in servers:
        for group in groups:
            _ = update_server(server, group, job)

    return "", "", ""
