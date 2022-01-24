import json
import uuid

from common.methods import set_progress
from infrastructure.models import Server
from resourcehandlers.maas.models import MaasResourceHandler


def run(job, *args, **kwargs):
    # the default for this input ('standard' or 'ovs') may be edited on the Action
    bridge_type = "{{ bridge_type }}"
    bridge_type = "standard"
    # machine is a MAAS-specific object, only available within the MaasWrapper
    machine = kwargs.get('machine', None)

    #server_id is the ID of the Cloudbolt Server being provisioned
    server_id = kwargs.get('server_id', None)
    cb_server = Server.objects.get(pk=server_id)

    if machine:
        maas_id = machine['system_id']
        set_progress("The MaaS plugin will operate on MAAS machine {}, Cloudbolt Server id = {}".format(maas_id, server_id))
    else:
        return "FAILURE", "", "Missing required MAAS machine info."

    # The technology-specific wrapper has methods for certain calls to MAAS
    wrapper = kwargs.get('wrapper', None)

    is_physical = kwargs.get('physical', False)
    if is_physical:
        set_progress("Provisioning a physical MAAS machine.")

        # get interfaces for this server:
        interfaces = wrapper.maas_api_request("GET", "nodes/{}/interfaces/".format(maas_id))
        
        # disconnect the bond0 interface
        bond0_ids = [iface['id'] for iface in interfaces if 'bond0' in iface['name']]
        if bond0_ids:
            set_progress("Disconnecting interface {}".format(bond0_ids[0]))
            # wrapper.maas_api_request("POST", "nodes/{}/interfaces/{}/?op=disconnect".format(maas_id, bond0_ids[0]))
            
        # create a bridge
        if interfaces:
            set_progress("Creating a bridge {}".format(interfaces[0].get('mac_address')))
            data = {
                "name": "br0",
                "mac_address": interfaces[0]['mac_address'],
                "bridge_type": bridge_type,
                "parent" : interfaces[0]['id'],
                "bridge_stp": False
            }
            print("maas_id",maas_id)
            
            
            wrapper.maas_api_request("POST", "nodes/{}/interfaces/?op=create_bridge".format(maas_id),data=data)
    else:
        set_progress("Provisioning a virtual machine on a MAAS LXD host.")

    return "SUCCESS", "The MaaS during-provisioning plugin has completed.", ""
