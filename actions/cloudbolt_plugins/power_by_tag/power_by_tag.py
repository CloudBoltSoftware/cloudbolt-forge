from infrastructure.models import Server
from tags.models import TaggedItem

"""
Action used to control server power by tag name.

USE CASE: An admin wants to control how a set of servers is powered down. These
servers are tagged according to their priority group in CloudBolt. These groups
are power-01 and power-02. Servers tagged with power-01 should be powered down
before servers tagged with power-02.

This script could be added to a service blueprint as actions that get executed
in a specific order to control server power by tag.
"""


def run(job, **kwargs):
    for tag in TaggedItem.objects.filter(tag__name='{{ tag_name }}'):
        s = tag.content_object
        if isinstance(s, Server):
            if 'ON' == '{{ desired_power_state }}':
                s.power_on()
            elif 'OFF' == '{{ desired_power_state }}':
                s.power_off()
    return "", "", ""
