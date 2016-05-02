import unittest
from src.application import app


class MetricsTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
