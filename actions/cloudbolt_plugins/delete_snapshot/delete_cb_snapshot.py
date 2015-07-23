"""
CloudBolt Plug-in that deletes the snapshot for a VMware VM that was initiated by CB.

Does not affect snapshots created directly in VMware.

If there is no snapshot initiated by CB for the server, it does nothing.
"""
from infrastructure.models import ServerSnapshot
from jobs.models import (Job, DeleteSnapshotsParameters)
from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)


def run(job, *args, **kwargs):
    try:
        servers = job.server_set.all()
        for server in servers:
            job.set_progress("Checking server {} for snapshots...".format(server))
            snapshots = ServerSnapshot.objects.filter(server_id=server.id)
            if not snapshots:
                job.set_progress('No snapshots exist for server {}'.format(server))
                continue

            logger.info("Found snapshot, noting for deletion...")
            job_params = DeleteSnapshotsParameters.objects.create()
            job_params.snapshots.add(*snapshots)

            logger.info("Creating job...")
            child_job = Job(
                type="delete_snapshots",
                job_parameters=job_params,
                owner=job.owner,
                parent_job=job,
            )
            child_job.save()
            child_job.server_set.add(server)

            msg = (' Job #{} has been created to delete {} snapshot{} from server '
                   '{}.').format(
                child_job.pk, len(snapshots),
                's' if len(snapshots) > 1 else '', server)
            job.set_progress(msg)
        job.set_progress('Finished looking for snapshots on servers. Check child' +
                         ' job(s) for progress updates.')
    except Exception as err:
        return ('FAILURE', '', err)

    return ('', '', '')
