import requests

from utilities.decorators import json_view
from utilities.logger import ThreadLogger
from utilities.rest import RestConnection

logger = ThreadLogger(__name__)


@json_view
def fetch_data_from_api(request):
    with RandomUserConnection() as conn:
        response = conn.get('/')
        response.raise_for_status()
        return response.json()


class RandomUserConnection(RestConnection):

    def __init__(self) -> None:
        self.base_url = "https://randomuser.me/api"
        self.headers = {'Accept': 'application/json'}
        super().__init__(None, None)

    def __getattr__(self, item):
        if item == "get":
            return lambda url, **kwargs: requests.get(
                f"{self.base_url}", headers=self.headers, auth=None, **kwargs
            )
        elif item in ["post", "delete", "put", "patch"]:
            raise NotImplementedError
        else:
            return item
