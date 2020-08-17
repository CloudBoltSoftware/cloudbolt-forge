import requests
import json

from utilities.logger import ThreadLogger
from utilities.models import ConnectionInfo

logger = ThreadLogger(__name__)

DEFAULT_API_VERSION = '310'
HYPERVISOR_TYPES = ['VMWARE', 'RHEV', 'HYPERV', 'OPENSTACK', 'XENSERVER']
__version__ = '1.0'


class Tintri(object):

    def __init__(self):
        ci = ConnectionInfo.objects.filter(name__iexact='Tintri Appliance Endpoint').first()
        self.connection_info = ci
        self.api_version = '310'
        self.session_id = self.get_session_id(ci)

    def verify_connection(self, proto=None, ip=None, port=None, username=None, password=None):
        if proto and ip and port and username and password:
            ci = ConnectionInfo(name="test", protocol=proto, ip=ip, port=port,
                                username=username, password=password)
        else:
            ci = self.get_connection_info()

        # no exceptions means success
        self.get_session_id(ci)

    def get_connection_info(self):
        return self.connection_info

    def get_base_url(self, connection_info=None, include_version=True):
        if not connection_info:
            connection_info = self.get_connection_info()
        url = connection_info.format_url(auth=False) + "/api"

        if include_version:
            url += "/v{}".format(self.api_version)

        return url

    def get_session_id(self, connection_info=None):

        if not connection_info:
            connection_info = self.connection_info
        if not connection_info:
            return None

        login_username = connection_info.username
        login_password = connection_info.password

        headers = {'content-type': 'application/json', 'Tintri-Api-Client': self.__get_client_header()}
        data = {"username": login_username, "password": login_password,
                "typeId": "com.tintri.api.rest.vcommon.dto.rbac.RestApiCredentials"}
        login_url = '{}/session/login'.format(self.get_base_url(connection_info))

        httpresp = requests.post(login_url, json.dumps(data), headers=headers, verify=False)

        if httpresp.status_code is not 200:
            err = 'Failed to authenticate to {} as user {}. HTTP status code: {}'.format(
                login_url, login_username, httpresp.status_code)
            try:
                json_error = json.loads(httpresp.text)
            except Exception as e:
                raise Exception(err)
            raise Exception(json_error['code'], json_error['message'], json_error['causeDetails'])
        return httpresp.cookies['JSESSIONID']

    def __get_version(self, connection_info=None):
        if not self.__version:

            if not connection_info:
                connection_info = self.get_connection_info()
            headers = {'content-type': 'application/json'}
            versionUrl = '{}/info'.format(self.get_base_url(connection_info, include_version=False))
            httpResp = requests.get(versionUrl, headers=headers, verify=False)
            if httpResp.status_code is not 200:
                err = 'Failed to retrieve info page. HTTP status code: %d' % httpResp.status_code
                raise Exception(err)
            self.__version = json.loads(httpResp.text).get('preferredVersion')
        return self.__version

    def __get_client_header(self):
        default_header = 'Tintri-PythonSDK-%s' % __version__
        return default_header


    def get_appliance_info(self):
        headers = {'content-type': 'application/json'}
        if self.session_id:
            headers['cookie'] = 'JSESSIONID=%s' % self.session_id
        else:
            raise Exception("Not Logged in.")
        url = '{}/appliance'.format(self.get_base_url())
        httpresp = requests.get(url, headers=headers, verify=False)
        return httpresp.json()[0].get('info')

    def api_get(self, url, as_json=True):
        headers = {'content-type': 'application/json'}
        if self.session_id:
            headers['cookie'] = 'JSESSIONID=%s' % self.session_id
        else:
            raise Exception("Not Logged in.")
        if url.startswith("http"):
            uri = url
        else:
            uri = "/".join([self.get_base_url(), url])

        logger.info("tintri url: {}".format(uri))
        httpresp = requests.get(uri, headers=headers, verify=False)
        logger.info(httpresp)
        if as_json:
            httpresp = httpresp.json()
        return httpresp

    def api_post(self, url, payload):
        headers = {'content-type': 'application/json'}
        if url.startswith("http"):
            uri = url
        else:
            uri = "/".join([self.get_base_url(), url])

        body = payload
        if self.session_id:
            headers['cookie'] = 'JSESSIONID=%s' % self.session_id
        else:
            raise Exception("Not Logged in.")

        httpResp = requests.post(uri, headers=headers, data=json.dumps(body), verify=False)
        return httpResp


    def is_vmstore(self):
        headers = {'content-type': 'application/json'}
        versionUrl = self.get_base_url(include_version=False) + "/info"
        httpResp = requests.get(versionUrl, headers=headers, verify=False)
        if httpResp.status_code is not 200:
            err = 'Failed to retrieve info page. HTTP status code: %d' % httpResp.status_code
            raise Exception(err)

        return httpResp.json().get('productName') == 'Tintri VMstore'

    def is_tgc(self):
        headers = {'content-type': 'application/json'}
        versionUrl = self.get_base_url(include_version=False) + "/info"
        httpResp = requests.get(versionUrl, headers=headers, verify=False)
        if httpResp.status_code is not 200:
            err = 'Failed to retrieve info page. HTTP status code: %d' % httpResp.status_code
            raise Exception(err)

        return httpResp.json().get('productName') == 'Tintri Global Center'

    def get_vms(self, name):
        url = f'vm?name={name}'
        httpResp = self.api_get(url, as_json=False)
        return httpResp

    def get_vm_historic_stats(self, uuid, since, until):
        url = f'vm/{uuid}/statsHistoric?since={str(since)}'
        return self.api_get(url)

    def create_snapshot(self, consistency, retentionMinutes, snapshotName, sourceVmTintriUUID):
        headers = {'content-type': 'application/json'}
        url = '/flex/snapshot/action=create'
        #            ?consistency={consistency}&retentionMinutes={retentionMinutes}&snapshotName={snapshotName}&sourceVmTintriUUID={sourceVmTintriUUID}'
        # sourceVmTintriUUID = self.get_vms(name='ESXi-6.0').json().get('items')[0].get("uuid").get("uuid")

        body = {
            "sourceVmTintriUUID": f"{sourceVmTintriUUID}",
            "retentionMinutes": f"{retentionMinutes}",
            "consistency": f"{consistency}",
            "snapshotName": f"{snapshotName}",
            "replicaRetentionMinutes": 0,
            "typeId": "com.tintri.api.rest.v310.dto.domain.beans.snapshot.SnapshotSpec"
        }

        httpResp = self.api_post(url, body)
        return httpResp.json()

    def clone_vm(self, cloneVmName, vm_uuid, consistency, count=1, dstore_name='default'):
        headers = {'content-type': 'application/json'}
        url = f'https://{self.host}/api/v{self.api_version}/flex/vm/action=create'
        body = {
            "vmware": {
                "datastoreName": f"{dstore_name}",
                "folderMoref": None,
                "typeId": "com.tintri.api.rest.v310.dto.domain.beans.vm.VirtualMachineCloneSpec$VMwareCloneInfo",
                "hostClusterMoref": "C01",
                "customizationScript": None,
                "vCenterName": "10.50.1.10",
                "cloneVmName": f"{cloneVmName}"
            },
            "typeId": "com.tintri.api.rest.v310.dto.domain.beans.vm.VirtualMachineCloneSpec",
            "hyperv": None,
            "remoteCopyInfo": None,
            "restoreInfo": None,
            "vmId": f"{vm_uuid}",
            "rhev": None,
            "consistency": f"{consistency}",
            "count": count,
        }
        if self.session_id:
            headers['cookie'] = 'JSESSIONID=%s' % self.session_id
        else:
            raise Exception("Not Logged in.")

        httpResp = requests.post(url, headers=headers, data=json.dumps(body), verify=False)
        import pdb; pdb.set_trace()
        return httpResp.json()
