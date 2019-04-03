from datetime import datetime, timedelta
from queue import Queue, Empty
from random import randint
from time import sleep
from threading import Thread
from unittest import TestCase

from rekognition_face_search.poller import PollingImageSource
from rekognition_face_search.vxg_client import VXGClient


class MockVXGClient(VXGClient):
    """
    Emulating `rekognition_face_search.vxg_client.VXGClient` functions
    """
    def __init__(self):
        self.events = {}
        self.delay = 0

    def get_unprocessed_events(self, limit) -> (list, int):
        sleep(self.delay)
        return list(self.events.values())[:limit], len(self.events)

    def set_event_processing(self, event_id: int):
        sleep(self.delay)
        self.events[event_id].update({'meta': {VXGClient.TAG_PROCESSING: ''}})


def generate_events(count: int) -> dict:
    """
    Generate random event in format that VXG Server returns
    :param count: number of events to generate
    """
    return {
        idx: {
            'id': idx,
            'name': 'facedetection',
            'camid': randint(0, 1000),
            'time': (datetime.utcnow() - timedelta(seconds=idx)).isoformat(),
            'thumb': {
                'height': 720,
                'width': 1280,
                'time': (datetime.utcnow() - timedelta(seconds=idx)).isoformat(),
                'url': 'http://dummy.s3.amazonaws.com/%d' % idx,
                'size': 45000 + randint(0, 10000)
            }
        } for idx in range(count)}


class TestPollingImageSourceGetEvents(TestCase):
    def setUp(self):
        super(TestPollingImageSourceGetEvents, self).setUp()
        self.vxg_client = MockVXGClient()
        self.src = PollingImageSource(self.vxg_client, Queue())

    def test_get_events_no_events(self):
        events, more = self.src.get_events()
        self.assertEqual(len(events), 0)
        self.assertFalse(more)

    def test_get_events_few_events(self):
        self.vxg_client.events = generate_events(self.src.MAX_EVENT_BATCH - 1)
        events, more = self.src.get_events()
        self.assertEqual(len(events), len(self.vxg_client.events))
        self.assertFalse(more)

    def test_get_events_many_events(self):
        self.vxg_client.events = generate_events(self.src.MAX_EVENT_BATCH + 1)
        events, more = self.src.get_events()
        self.assertEqual(len(events), self.src.MAX_EVENT_BATCH)
        self.assertTrue(more)


class TestPollingImageSourcePollEvents(TestCase):
    def setUp(self):
        super(TestPollingImageSourcePollEvents, self).setUp()
        self.vxg_client = MockVXGClient()
        self.queue = Queue()
        self.src = PollingImageSource(self.vxg_client, self.queue)

    def test_poll_events_no_events(self):
        more = self.src.poll_events()
        self.assertFalse(more)
        self.assertEqual(self.queue.qsize(), 0)

    def test_poll_events_few_events(self):
        self.vxg_client.events = generate_events(PollingImageSource.MAX_EVENT_BATCH - 1)
        more = self.src.poll_events()
        self.assertFalse(more)
        self.assertEqual(len(self.vxg_client.events), self.queue.qsize())
        self.validate_queue_content()

    def test_poll_events_many_events(self):
        self.vxg_client.events = generate_events(PollingImageSource.MAX_EVENT_BATCH + 1)
        more = self.src.poll_events()
        self.assertTrue(more)
        self.assertEqual(PollingImageSource.MAX_EVENT_BATCH, self.queue.qsize())
        self.validate_queue_content()

    def validate_queue_content(self):
        item = self.queue.get_nowait()
        try:
            while True:
                self.assertEqual(self.vxg_client.events[item['id']]['thumb']['url'], item['url'])
                item = self.queue.get_nowait()
        except Empty:
            pass


class TestPollingImageSourceRoutine(TestCase):
    def setUp(self):
        super(TestPollingImageSourceRoutine, self).setUp()
        self.vxg_client = MockVXGClient()
        self.queue = Queue()
        self.src = PollingImageSource(self.vxg_client, self.queue)
        self.thread = Thread(target=self.src.routine)

    def test_routine_sanity(self):
        self.thread.start()
        sleep(0.6)
        self.assertTrue(self.thread.is_alive())
        self.src.NEED_STOP.set()
        sleep(0)  # Just give a tick to a thread
        self.thread.join(timeout=1.1)

    # TODO: test various interruption scenarios, ie in the middle of server requests, awaiting while queue will be freed
