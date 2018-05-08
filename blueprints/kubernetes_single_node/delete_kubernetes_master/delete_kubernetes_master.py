"""
Deletes the Kubernetes orchestrator associated with this service. Used by the
Kubernetes Single Node blueprint.
"""
from containerorchestrators.kuberneteshandler.models import Kubernetes


def run(job=None, logger=None, resource=None, **kwargs):
    job.set_progress("Deleting the resource's container orchestrator")
    orchestrator_id = resource.create_k8s_cluster_id
    if orchestrator_id:
        kubernetes = Kubernetes.objects.get(id=orchestrator_id)
        kubernetes.delete()
        job.set_progress("Removed container orchestrator")
    else:
        job.set_progress("There is no container orchestrator to delete")