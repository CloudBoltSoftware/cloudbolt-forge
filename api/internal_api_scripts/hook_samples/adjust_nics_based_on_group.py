import logging

# Begin of customer defined parameters

SERVER_ROLE_CF = "dev_server_role"

NICS_PER_SERVER = {
    "APP": 1,
    "DB": 1,
    "MSG": 1,
    "WEB": 1,
    "GW": 1,
}

# End of customer defined parameters

#
# DO NOT EDIT BELLOW THIS LINE #
#


def run(job, logger=None):
    if not logger:
        logger = logging.getLogger(__name__)
    server = job.server_set.all()[0]
    group = server.group

    # get the target network we should set all nics on this server to
    nic_network = group.custom_field_options.filter(field__name="sc_nic_0")[0].value

    # get the server_role (used to look-up how many nics we should set
    server_role = server.get_value_for_custom_field(SERVER_ROLE_CF)

    msg = "Setting network on server {}[{}] to {}"
    job.set_progress(msg.format(server.hostname, server.id, str(nic_network)))

    if server_role not in NICS_PER_SERVER:
        job.set_progress("Unknonw server role: {}".format(server_role))
        total_nics_to_set = 0
    else:
        total_nics_to_set = NICS_PER_SERVER[server_role]

    i = 0
    while i < total_nics_to_set:
        job.set_progress("Updating nic {}...".format(i + 1))
        field = "sc_nic_{}".format(i)
        server.set_value_for_custom_field(field, nic_network)
        server.save()
        i += 1

    return "", "", ""
