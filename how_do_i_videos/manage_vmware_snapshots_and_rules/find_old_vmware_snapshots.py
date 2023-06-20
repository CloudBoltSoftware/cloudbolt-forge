#!/usr/bin/env python


if __name__ == "__main__":
    import django

    django.setup()

import datetime
from common.methods import set_progress

from resourcehandlers.vmware import pyvmomi_wrapper
from resourcehandlers.vmware.models import VsphereResourceHandler

from django.utils import timezone
import utilities

THRESHOLD_DAYS = "{{ threshold_days }}"
try:
    THRESHOLD_DAYS = int(THRESHOLD_DAYS)
except ValueError:
    set_progress("No threshold days specified, defaulting to 365 days.")
    THRESHOLD_DAYS = 365

now = timezone.make_aware(datetime.datetime.now(),
                          timezone.get_default_timezone())
AGE_THRESHOLD = now - datetime.timedelta(days=THRESHOLD_DAYS)

# Default DRY_RUN to True if the template substitution isn't happening
if "{{ dry_run }}" == "False":
    DRY_RUN = False
else:
    DRY_RUN = True

RH_IDS = {{rh_ids}}


def generate_options_for_rh_ids(field, **kwargs):
    rhs = VsphereResourceHandler.objects.exclude(name__contains="unstable")
    return [(rh.id, rh.name) for rh in rhs]


def format_snapshot_desc(snapshot):
    """
    :param snapshot: a VMware snapshot object
    :return: a user-facing string representing that snapshot
    """
    create_date = "{}/{}/{}".format(
        snapshot.createTime.year, snapshot.createTime.month,
        snapshot.createTime.day
    )
    desc = "[{}] {}".format(create_date, snapshot.name)
    if snapshot.description:
        desc = "{}- {}".format(desc, snapshot.description)
    return desc


def get_snapshots_for_handler(rh, age_threshold):
    """
    Iterates over all active servers that CB knows about for this RH, fetches their snapshots,
    and returns the ones that are older than the threshold.

    :return: a list of two-tuples (CB server ID, VMware snapshot ID)
    """
    if DRY_RUN:
        set_progress("Dry run is enabled, snapshots will not be deleted.")
    else:
        set_progress("Dry run is not enabled, snapshots will be deleted.")
    si = rh.resource_technology.work_class._get_connection()
    servers = rh.server_set.exclude(
        status__in=["HISTORICAL", "DECOM", "PROVFAILED"])
    all_shots = []
    for server in servers:
        shots = []
        try:
            # TODO: move this logic into the VMware resource handler so this action can just call
            #  rh.get_snapshot_list_for_vm()
            shots = pyvmomi_wrapper.get_snapshot_list_for_vm(
                si, server, age_threshold=age_threshold
            )
        except utilities.exceptions.NotFoundException as err:
            set_progress(str(err))
        if shots:
            shot_descs = [format_snapshot_desc(shot) for shot in shots]
            set_progress(
                "  VM '{}' has {}: {}".format(server, len(shots),
                                              ", ".join(shot_descs))
            )

            shots = [(server.id, shot.id) for shot in shots]
            all_shots.extend(shots)

    set_progress(
        "Found {} matching snapshots for {}".format(len(all_shots), rh))
    return all_shots


def check(job, logger, **kwargs):
    """
    Iterates over all vCenter resource handlers, finding all snapshots on all servers that are
    older than the age threshold.
    """
    # rhs = VsphereResourceHandler.objects.exclude(name__contains="unstable")
    set_progress(
        "Scanning {} vCenters for snapshots older than {}".format(
            len(RH_IDS), AGE_THRESHOLD
        ),
        total_tasks=len(RH_IDS),
    )
    rhs_done = 0
    all_shots = []
    for rh_id in RH_IDS:
        rh = VsphereResourceHandler.objects.get(id=rh_id)
        set_progress("Working on {}".format(rh), tasks_done=rhs_done)
        rh.init()
        shots = get_snapshots_for_handler(rh, AGE_THRESHOLD)
        all_shots.extend(shots)
        rhs_done += 1
    set_progress("Found {} matching snapshots total".format(len(all_shots)))

    snaps_to_delete = {
        "snapshots": all_shots} if all_shots and not DRY_RUN else {}

    return "", "", "", snaps_to_delete


if __name__ == "__main__":
    print(check(job=None, logger=None))