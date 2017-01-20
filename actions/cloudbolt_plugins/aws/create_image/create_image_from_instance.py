from common.methods import set_progress
from infrastructure.models import Server

def run(job, logger=None):
    # Get server & power status
    server = job.server_set.first()
    server_original_power_status = server.power_status
    
    # Power off VM (optional)
    #if server_original_power_status != "POWEROFF":
    #    set_progress("Powering off server.")
    #    task = server.power_off()
    # -->add timeout here to wait for shutdown

    # Connect to AWS
    e = server.environment
    set_progress("Connecting to EC2 region {}.".format(e.aws_region), logger, job)
    rh = server.resource_handler
    aws = rh.cast()
    aws.connect_ec2(e.aws_region)
    ec2 = aws.resource_technology.work_class.ec2

    # Get instance-id & region
    instance_id = server.resource_handler_svr_id

    # Create AMI from instance
    #http://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/Creating_EBSbacked_WinAMI.html
    ec2.create_image(instance_id, name='{{ AMIname }}', description='Created via CloudBolt')
    return "","",""
