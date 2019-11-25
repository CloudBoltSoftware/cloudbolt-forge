"""
Teardown the CloudBolt resources (container_orchestrator, environment)
associated with this Kubernetes cluster.
"""
from django.core.exceptions import ObjectDoesNotExist
from common.methods import set_progress
from containerorchestrators.kuberneteshandler.models import Kubernetes
from utilities.run_command import execute_command


def run(job, *args, **kwargs):
    resource = job.resource_set.first()
    
    try:
        container_orchestrator = Kubernetes.objects.get(id=resource.container_orchestrator_id)
        environment = container_orchestrator.environment_set.first()
    
        container_orchestrator.delete()
        environment.delete()
    except ObjectDoesNotExist:
        set_progress("Could not find container orchestrator for this resource.")

    resource_dir = '/var/opt/cloudbolt/kubernetes/resource-{}'.format(resource.id)
    execute_command('rm -rf {}'.format(resource_dir))
