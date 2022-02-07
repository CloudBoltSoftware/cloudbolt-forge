"""
This is a MAAS-specific sample of plug-in code for a 'During Resource Provisioning' Action.
Please see the Plugin Actions documentation for more examples of plug-in code:
https://docs.cloudbolt.io/articles/#!cloudbolt-latest-docs/cloudbolt-plug-ins
"""
import json
import uuid

from common.methods import set_progress
from infrastructure.models import Server
from resourcehandlers.maas.models import MaasResourceHandler


def run(job, *args, **kwargs):
    set_progress("This will show up in the job details page in the CB UI, and in the job log")
    mount_point = "{{ filesystem_mount_point }}"
    
    # machine is a MAAS-specific object, only available within the MaasWrapper
    machine = kwargs.get('machine', None)
    
    #server_id is the ID of the Cloudbolt Server being provisioned
    server_id = kwargs.get('server_id', None)
    cb_server = Server.objects.get(pk=server_id)

    # maas_machine_type = True when create virtual machine else False
    if  cb_server.maas_machine_type:
        set_progress("Provisioning a RAID is not valid for the virtual machine on a MAAS LXD host")
        return "SUCCESS", "The MaaS during-provisioning plugin has completed.", ""

    if machine:
        maas_id = machine['system_id']
        set_progress("Configuring RAID on MAAS machine {}".format(maas_id))
    else:
        return "FAILURE", "", "Missing required MAAS machine info."

    wrapper = kwargs.get('wrapper', None)
    if wrapper:
        vm = wrapper.get_vm('unused', maas_id)
        machine = wrapper.driver.get_machine(maas_id)
    else:
        return "FAILURE", "", "Invalid (None) wrapper passed to plugin"

    fstype = "ext4"
    # remove any existing RAID configurations
    raids = wrapper.maas_api_request("GET", "nodes/{}/raids/".format(maas_id))
    
    # We need to move to machine in ready state to delete the existig raid, you can't delete raid if machine in allocated state
    rel = wrapper.maas_api_request("POST", "machines/{}/?op=release".format(maas_id), data = {"comment" : "making in ready state" })
    if raids:
        for raid in raids:
            set_progress("Deleting RAID volume: {}".format(raid['name']))
            wrapper.maas_api_request("DELETE", "nodes/{}/raid/{}/".format(maas_id, raid['id']))
            
    # get unused physical disks
    all_disks = wrapper.maas_api_request("GET", "nodes/{}/blockdevices/".format(maas_id))
    disks = [str(disk['id']) for disk in all_disks if disk['used_for'] == 'Unused' and disk['type'] == 'physical']
    set_progress("MaaS machine has {} associated disks, of which {} are unused physical disks.".format(len(all_disks), len(disks)))
    
    if  len(disks)>=2:
        set_progress("Creating a RAID-1 array md0 for the machine using all unused disks: {}".format(','.join([disk['name'] for disk in all_disks if disk['used_for'] == 'Unused' and disk['type'] == 'physical'])))
        data={
            "name": "md0",
            "uuid": uuid.uuid4(),
            "level": 'raid-1',
            "block_devices": disks,
            "partitions": [],
            "spare_devices": [],
            "spare_partitions": [],
            }

        resp = wrapper.maas_api_request("POST", "nodes/{}/raids/".format(maas_id), data= data)
        block_device_id = resp["virtual_device"]["id"]
        
        set_progress("Formatting filesystem: block_device_id={}, fstype={}".format(block_device_id, fstype))
        formatdata ={
            'fstype': fstype, 
            'uuid': uuid.uuid4()
        }
        formatres = wrapper.maas_api_request("POST", 'nodes/{}/blockdevices/{}/?op=format'.format(maas_id, block_device_id), data = formatdata)
        
        set_progress("Configuring mount point: block_device_id={}, mount_point={}".format(block_device_id, mount_point))
        mountdata={
            "mount_point": mount_point,
            "mount_options": "",
        }
        mountres = wrapper.maas_api_request("POST", 'nodes/{}/blockdevices/{}/?op=mount'.format(maas_id, block_device_id), data = mountdata)
        allocated_machines = wrapper.maas_api_request("POST", "machines/?op=allocate", data = {'system_id' : maas_id})
        set_progress('Reallocation of MaaS Machine: {}'.format(maas_id))

        return "SUCCESS", "Finished configuring RAID for MaaS machine", ""
    else:
        return "FAILURE", "", "Failed to create RAID during-provisioning because only {} disk, It should be have more than 2 disks".format(disks)