#!/usr/bin/env python
'''
This script should be run just once from the C2 root folder
(/opt/cloudbolt on most instances)
'''

if __name__ == '__main__':
    import django
    django.setup()

from history.models import ServerHistory
from utilities.events import update_or_create_summary_event


def main():
    for h in ServerHistory.objects.filter(event_type='ONBOARD'):
        msg = 'Adding onboard event on {} to group {}'.format(
            h.action_time.date(), h.server.group
        )
        print msg
        update_or_create_summary_event(
            h.server.group, 1, h.cpu_cnt, h.mem_size,
            h.disk_size, h.server.get_rate(), h.action_time.date()
        )

if __name__ == '__main__':
    main()
