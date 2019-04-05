import requests
from time import sleep
from threading import Thread
from unittest import TestCase

from rekognition_face_search.web import WebApplication


class MockApplication:
    def __init__(self):
        self.server_uri = None
        self.token = None
        self.collection = None
        self.access_key = None
        self.secret_key = None


class TestWebApplicationRoutine(TestCase):
    def setUp(self):
        self.web = WebApplication(MockApplication())
        self.thread = Thread(target=self.web.routine)

    def test_web_application_routine_sanity(self):
        self.thread.start()
        sleep(0.1)
        resp = requests.get('http://127.0.0.1:%d/settings/' % self.web.port)
        self.assertEqual(resp.status_code, 200)
        self.web.stop()
        self.thread.join(timeout=1)
