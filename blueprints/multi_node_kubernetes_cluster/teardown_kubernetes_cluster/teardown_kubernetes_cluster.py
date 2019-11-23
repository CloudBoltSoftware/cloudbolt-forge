"""
Teardown the CloudBolt resources (container_orchestrator, environment)
associated with this Kubernetes cluster.
"""
from common.methods import set_progress
from containerorchestrators.kuberneteshandler.models import Kubernetes
from utilities.run_command import execute_command


def run(job, *args, **kwargs):
    resource = job.resource_set.first()
    
    container_orchestrator = Kubernetes.objects.get(id=resource.container_orchestrator_id)
    environment = container_orchestrator.environment_set.first()
    
    container_orchestrator.delete()
    environment.delete()

    resource_dir = '/var/opt/cloudbolt/kubernetes/resource-{}'.format(resource_id)
    execute_command('rm -rf {}'.format(RESOURCE_LOCATION))
