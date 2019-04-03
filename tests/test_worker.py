import os
from queue import Queue, Empty
from unittest import TestCase, skipUnless

from rekognition_face_search.aws_client import AWSClient
from rekognition_face_search.vxg_client import VXGClient
from rekognition_face_search.worker import Worker


AWS_TEST_CREDENTIALS = {
    'collection_id': (os.environ.get('COLLECTION_ID') + '_test') if os.environ.get('COLLECTION_ID') else None,
    'access_key': os.environ.get('ACCESS_KEY'),
    'secret_key': os.environ.get('SECRET_KEY'),
}


class MockVXGClient(VXGClient):
    def __init__(self):
        self.events = {}

    def set_event_processed(self, event_id: int, faces: list):
        self.events[event_id] = faces


class MockAWSClient(AWSClient):
    def __init__(self):
        pass


class TestWorkerProcess(TestCase):
    def setUp(self):
        super(TestWorkerProcess, self).setUp()
        self.queue = Queue()
        self.aws = MockAWSClient()
        self.vxg = MockVXGClient()
        self.worker = Worker(self.queue, self.aws, self.vxg)

    def test_process_no_events(self):
        self.worker.QUEUE_TIMEOUT = 0.1
        with self.assertRaises(Empty):
            self.worker.process()


@skipUnless(all((AWS_TEST_CREDENTIALS['collection_id'],
                 AWS_TEST_CREDENTIALS['access_key'],
                 AWS_TEST_CREDENTIALS['secret_key'])),
            'Valid credentials from environment variables are required to run integration tests')
class TestWorkerProcessIntegration(TestCase):
    def setUp(self):
        super(TestWorkerProcessIntegration, self).setUp()
        self.queue = Queue()
        self.aws = AWSClient(**AWS_TEST_CREDENTIALS)
        self.vxg = MockVXGClient()
        self.worker = Worker(self.queue, self.aws, self.vxg)

    def test_process_single(self):
        self.worker.queue.put_nowait({'id': 0, 'url': 'https://upload.wikimedia.org/wikipedia/commons/3/33/Jeff_Bezos_2016.jpg'})
        self.worker.process()
        self.assertIn(0, self.vxg.events)

    # TODO: test image unavailable issue (connectivity or 404), postpone image processing for 1 minute
    # TODO: test AWS connectivity issues
    # TODO: test VXG Server connectivity issue
