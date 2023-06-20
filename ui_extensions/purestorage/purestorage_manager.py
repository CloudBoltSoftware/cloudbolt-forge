'''
Class to manage Purestorage operations
'''
from datetime import datetime

class PureStorageManager(object):
    def __init__(self):
        self._volumes = [
            {
                u'serial': u'DABA29111570F7A4000114C0',
                u'size': 1073741824,
                u'name': u'vol1',
                u'created': datetime.strptime('2014-08-11T17:19:35Z','%Y-%m-%dT%H:%M:%SZ')
            },
            {
                u'serial': u'DABA29111570F7A4000114C1',
                u'size': 524288000,
                u'name': u'vol2',
                u'created': datetime.strptime('2014-08-11T17:19:51Z','%Y-%m-%dT%H:%M:%SZ')
            }
        ]
        self._snapshots = [
            {
                u'source': u'vol1',
                u'serial': u'DABA29111570F7A4000115A4',
                u'size': 1073741824,
                u'name': u'vol1.together',
                u'created': datetime.strptime('2014-08-15T17:21:58Z','%Y-%m-%dT%H:%M:%SZ')
            },
            {
                u'source': u'vol2',
                u'serial': u'DABA29111570F7A4000115A5',
                u'size': 5242880,
                u'name': u'vol2.together',
                u'created': datetime.strptime('2014-08-15T17:21:58Z','%Y-%m-%dT%H:%M:%SZ')
            },
            {
                u'source': u'vol2',
                u'serial': u'DABA29111570F7A4000115A3',
                u'size': 5242880,
                u'name': u'vol2.5539',
                u'created': datetime.strptime('2014-08-15T17:21:22Z','%Y-%m-%dT%H:%M:%SZ')
            }
        ]

    def get_volumes(self):
        return self._volumes

    def get_snapshots(self):
        return self._snapshots
