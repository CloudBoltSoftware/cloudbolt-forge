import requests

from utilities.logger import ThreadLogger
from utilities.rest import RestConnection

logger = ThreadLogger(__name__)

KUMO_WEB_HOST = "https://realdata.kumolus.co"
KUMO_API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMGM5YWM1YTEtMDEwNi00NWE0LWJmMTYtZTBjMTllMTkwMjMyIiwiZW1haWwiOiJldmVudHNAa3Vtb2x1cy5jb20iLCJhY2NvdW50X2lkIjoiNmI5NmMwODQtNjczZC00YTBkLWE5NWYtNWFiZjZlMjU5YzdiIiwic3ViZG9tYWluIjoicmVhbGRhdGEiLCJpYXQiOjE2MTMzOTI0NDd9.OEnk4Vam0VWSZbBO4eawIzaHZpHiCe8kHPVp5FB02p8"
BASE_URL = KUMO_WEB_HOST + "/reportapi/api/v1"


class KumoConnector(RestConnection):

    def __init__(self, base_url=BASE_URL):
        super().__init__(None, None)
        self.pwd = KUMO_API_KEY
        self.base_url = base_url

    def __enter__(self):
        self.headers = {
            'Authorization': f'Bearer {self.pwd}',
            'Accept': "application/json",
            'web-host': KUMO_WEB_HOST
        }
        return super().__enter__()

    def __getattr__(self, item):
        if item == 'get':
            return lambda path, params=None, **kwargs: self.get_handler(
                path, params, **kwargs)
        elif item == 'post':
            return lambda path, json, **kwargs: self.post_handler(
                path, json, **kwargs)

    def post_handler(self, path, json, **kwargs):
        headers = kwargs.get("headers", None)
        if headers:
            self.headers.update(headers)
        url = f'{self.base_url}{path}'
        return requests.post(url, headers=self.headers, json=json, **kwargs)

    def get_handler(self, path, params, **kwargs):
        headers = kwargs.get("headers", None)
        if headers:
            self.headers.update(headers)
        logger.info(self.headers)
        url = f'{self.base_url}{path}'
        return requests.get(url, headers=self.headers, params=params, **kwargs)
