import requests
import json

DEFAULT_API_VERSION = '310'
__version__ = '1.0'


class Tintri(object):
    def __init__(self, host, username=None, password=None, api_version=DEFAULT_API_VERSION):
        self.session_id = None
        self.__version = None
        self.host = host
        self.username = username
        self.password = password

        self.api_version = api_version

    def __get_version(self):
        if not self.__version:
            headers = {'content-type': 'application/json'}
            versionUrl = 'https://%s/api/info' % self.host
            httpResp = requests.get(versionUrl, headers=headers, verify=False)
            if httpResp.status_code is not 200:
                err = 'Failed to retrieve info page. HTTP status code: %d' % httpResp.status_code
                raise Exception(err)
            self.__version = json.loads(httpResp.text).get('preferredVersion')
        return self.__version

    def __get_client_header(self):
        default_header = 'Tintri-PythonSDK-%s' % __version__
        return default_header

    def login(self, username=None, password=None):
        self.__get_version()

        if (username is None and self.username is None) or (password is None and self.password is None):
            raise Exception("Username and password need to be provided either at object instantiation or at login")

        login_username = self.username if not username else username
        login_password = self.password if not password else password

        headers = {'content-type': 'application/json', 'Tintri-Api-Client': self.__get_client_header()}
        data = {"username": login_username, "password": login_password,
                "typeId": "com.tintri.api.rest.vcommon.dto.rbac.RestApiCredentials"}
        login_url = 'https://%s/api/v%s/session/login' % (self.host, self.api_version)

        httpresp = requests.post(login_url, json.dumps(data), headers=headers, verify=False)

        if httpresp.status_code is not 200:
            err = 'Failed to authenticate to %s as user %s pwd %s. HTTP status code: %d' % (
                self.host, self.username, self.password, httpresp.status_code)
            try:
                json_error = json.loads(httpresp.text)
            except Exception as e:
                raise Exception(err)
            raise Exception(json_error['code'], json_error['message'], json_error['causeDetails'])
        self.session_id = httpresp.cookies['JSESSIONID']
        return httpresp.json()

    def get_appliance_info(self):
        headers = {'content-type': 'application/json'}
        if self.session_id:
            headers['cookie'] = 'JSESSIONID=%s' % self.session_id
        else:
            raise Exception("Not Logged in.")
        url = 'https://%s/api/v%s/appliance' % (self.host, self.api_version)
        httpresp = requests.get(url, headers=headers, verify=False)
        return httpresp.json()[0].get('info')

    def is_vmstore(self):
        headers = {'content-type': 'application/json'}
        versionUrl = 'https://%s/api/info' % self.host
        httpResp = requests.get(versionUrl, headers=headers, verify=False)
        if httpResp.status_code is not 200:
            err = 'Failed to retrieve info page. HTTP status code: %d' % httpResp.status_code
            raise Exception(err)

        return httpResp.json().get('productName') == 'Tintri VMstore'

    def is_tgc(self):
        headers = {'content-type': 'application/json'}
        versionUrl = 'https://%s/api/info' % self.host
        httpResp = requests.get(versionUrl, headers=headers, verify=False)
        if httpResp.status_code is not 200:
            err = 'Failed to retrieve info page. HTTP status code: %d' % httpResp.status_code
            raise Exception(err)

        return httpResp.json().get('productName') == 'Tintri Global Center'

    def get_vms(self, name):
        headers = {'content-type': 'application/json'}
        url = f'https://{self.host}/api/v{self.api_version}/vm?name={name}'
        if self.session_id:
            headers['cookie'] = 'JSESSIONID=%s' % self.session_id
        else:
            raise Exception("Not Logged in.")

        httpResp = requests.get(url, headers=headers, verify=False)
        return httpResp

    def get_vm_historic_stats(self, uuid, since, until):
        headers = {'content-type': 'application/json'}
        url = f'https://{self.host}/api/v{self.api_version}/vm/{uuid}/statsHistoric?since={str(since)}'
        if self.session_id:
            headers['cookie'] = 'JSESSIONID=%s' % self.session_id
        else:
            raise Exception("Not Logged in.")

        httpResp = requests.get(url, headers=headers, verify=False)
        return httpResp.json()

    def create_snapshot(self, consistency, retentionMinutes, snapshotName, sourceVmTintriUUID):
        headers = {'content-type': 'application/json'}
        url = f'https://{self.host}/api/v{self.api_version}/flex/snapshot/action=create'
        #            ?consistency={consistency}&retentionMinutes={retentionMinutes}&snapshotName={snapshotName}&sourceVmTintriUUID={sourceVmTintriUUID}'
        #sourceVmTintriUUID = self.get_vms(name='Ubuntu 18.04').json().get('items')[0].get("uuid").get("uuid")

        body = { 
                "sourceVmTintriUUID": f"{sourceVmTintriUUID}",
                "retentionMinutes": f"{retentionMinutes}",
                "consistency": f"{consistency}",
                "snapshotName": f"{snapshotName}",
                "replicaRetentionMinutes": 0,
                "typeId": "com.tintri.api.rest.v310.dto.domain.beans.snapshot.SnapshotSpec"
        }

        if self.session_id:
            headers['cookie'] = 'JSESSIONID=%s' % self.session_id
        else:
            raise Exception("Not Logged in.")

        httpResp = requests.post(url, headers=headers, data=json.dumps(body), verify=False)
        
        return httpResp.json()

