import os
from random import random
from unittest import TestCase, skipUnless
from uuid import uuid4

from rekognition_face_search.vxg_client import VXGClient

VXG_TEST_CREDENTIALS = {
    'server_uri': os.environ.get('SERVER_URI'),
    'token': os.environ.get('TOKEN')
}


def generate_sample_faces(count: int) -> list:
    return [{
        'FaceId': str(uuid4()),
        'BoundingBox': {
            'Top': random(),
            'Left': random(),
            'Width': random(),
            'Height': random()
        }
    } for _ in range(count)]


@skipUnless(all((VXG_TEST_CREDENTIALS['server_uri'],
                 VXG_TEST_CREDENTIALS['token'])),
            'Valid credentials from environment variables are required to run integration tests')
class TestVXGClientIntegration(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vxg = VXGClient(**VXG_TEST_CREDENTIALS)

    def test_get_unprocessed_events(self):
        events, total = self.vxg.get_unprocessed_events(20)
        self.assertLessEqual(len(events), 20)
        for event in events:
            self.assertIn('id', event)
            event_details = self.vxg.get_event_details(event['id'])
            event_meta = event_details.get('meta', {})
            self.assertNotIn(self.vxg.TAG_PROCESSING, event_meta)
            self.assertNotIn(self.vxg.TAG_HAS_FACE, event_meta)
            self.assertNotIn(self.vxg.TAG_NO_FACE, event_meta)

    def test_event_processing(self):
        events, total = self.vxg.get_unprocessed_events(1)
        if len(events):
            event_id = events[0]['id']
            self.vxg.set_event_processing(event_id)
            event_after_set = self.vxg.get_event_details(event_id)
            self.assertIn(self.vxg.TAG_PROCESSING, event_after_set['meta'])
            self.vxg.clear_event_processing(event_id)
            event_after_clear = self.vxg.get_event_details(event_id)
            self.assertNotIn(self.vxg.TAG_PROCESSING, event_after_clear.get('meta', {}))

    def test_event_processed_has_faces(self):
        events, total = self.vxg.get_unprocessed_events(1)
        if len(events):
            event_id = events[0]['id']
            sample_faces = generate_sample_faces(3)
            sample_faces_copy = [dict(face) for face in sample_faces]
            self.vxg.set_event_processed(event_id, sample_faces_copy)
            event_after_set = self.vxg.get_event_details(event_id)
            self.assertIn(self.vxg.TAG_HAS_FACE, event_after_set['meta'])
            for sample_face in sample_faces:
                self.assertIn(self.vxg.TAG_FACE_FMT % sample_face['FaceId'], event_after_set['meta'])
            self.vxg.clear_event_processed(event_id, sample_faces)
            event_after_clear = self.vxg.get_event_details(event_id)
            self.assertNotIn(self.vxg.TAG_HAS_FACE, event_after_clear.get('meta', {}))
            for sample_face in sample_faces:
                self.assertNotIn(self.vxg.TAG_FACE_FMT % sample_face['FaceId'], event_after_clear.get('meta', {}))

    def test_event_processed_no_faces(self):
        events, total = self.vxg.get_unprocessed_events(1)
        if len(events):
            event_id = events[0]['id']
            self.vxg.set_event_processed(event_id, [])
            event_after_set = self.vxg.get_event_details(event_id)
            self.assertIn(self.vxg.TAG_NO_FACE, event_after_set['meta'])
            self.vxg.clear_event_processed(event_id, [])
            event_after_clear = self.vxg.get_event_details(event_id)
            self.assertNotIn(self.vxg.TAG_NO_FACE, event_after_clear.get('meta', {}))

    # TODO: test set_event_processed_error
