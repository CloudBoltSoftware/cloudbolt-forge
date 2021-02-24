from django.test import TestCase

from customer_settings import KUMO_API_KEY
from xui.kumo_integration_kit.kumo_wrapper import KumoConnector


class TestKumoConnector(TestCase):

    def test_get(self):
        with KumoConnector(token=KUMO_API_KEY) as conn:
            response = conn.get('/aws/reports/dashboard_charts')
            self.assertIn('response', response.json())

    def test_post(self):
        payload = {
            "daily": True,
            "group_by": "day",
            "date_range": {
                "start_date": "December 1, 2020",
                "end_date": "January 1, 2021"
            },
            "dimensions": [
                "account_id"
            ],
            "metrics": [
                "unblended"
            ],
            "account": [
                "336101051063"
            ],
            "region": [
            ],
            "multi_series": False
        }
        with KumoConnector(token=KUMO_API_KEY) as conn:
            response = conn.post(
                '/aws/reports/custom',
                json=payload
            )
            print(response.content)
            self.assertEqual(response.status_code, 200)
