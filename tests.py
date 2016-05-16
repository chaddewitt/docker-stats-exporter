import unittest
from src.application import app


class MetricsTestCase(unittest.TestCase):
    def test_get_metrics(self):
        client = app.test_client()
        resp = client.get('/metrics')
        self.assertEqual(resp.status_code, 200)
