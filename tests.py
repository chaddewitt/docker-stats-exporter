import unittest
from src.application import app


class MetricsTestCase(unittest.TestCase):
    def test(self):
        # TODO mock out cgroup files and add better assertions
        self.client = app.test_client()
        res = self.client.get("/metrics")
        self.assertEqual(res.status_code, 200)
