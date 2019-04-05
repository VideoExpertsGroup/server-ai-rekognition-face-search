from queue import Queue, Empty
from threading import Event
from time import sleep
import traceback

import requests

from .aws_client import AWSClient
from .vxg_client import VXGClient


class Worker:
    """
    Gets image URLs from the Queue and starts it's processing:
        1) downloads image from the storage;
        2) sends "search_faces_by_image" request to AWS Rekognition, get face UUID if someone familiar is found
        3) if no known faces is found, but there's a faces, call "index_faces" to add faces to Collection, get their UUIDs
        4) set metadata with face UUID and rectangle to this event, also set meta tag "processed_has_face"
        5) if no faces found set meta tag "processed_no_face"
    """
    QUEUE_TIMEOUT = 1

    def __init__(self, queue: Queue, aws_client: AWSClient, vxg_client: VXGClient):
        self.queue = queue
        self.aws = aws_client
        self.vxg = vxg_client
        self.need_stop = Event()

    def stop(self):
        self.need_stop.set()

    def routine(self):
        while not self.need_stop.wait(timeout=0.01):
            try:
                try:
                    self.process()
                except Empty:
                    pass
            except Exception as ex:
                print('Unexpected exception at PollingImageSource.routine: %s\n%s' % (ex, traceback.format_exc()))
                sleep(1)

    def process(self):
        """
        Process a single task in the queue. All the logic is placed here.
        """
        # Get task
        item = self.queue.get(timeout=self.QUEUE_TIMEOUT)
        try:
            # Download image
            img_resp = requests.get(item['url'])
            # Find faces at the image
            search_resp = self.aws.search_face(img_resp.content)
            if not search_resp['FaceMatches']:
                # If familiar faces are not found, index new faces to recognise them in the future
                index_resp = self.aws.index_faces(img_resp.content)
                faces = [face_record['Face'] for face_record in index_resp['FaceRecords']]
            else:
                # AWS looking only for the biggest face in the image, so let's simply find a best match
                # for this single face and report it to server
                best_match = None
                for match in search_resp['FaceMatches']:
                    if best_match is None or best_match['Similarity'] < match['Similarity']:
                        best_match = match
                faces = [best_match['Face']]
            self.vxg.set_event_processed(item['id'], faces)
            self.vxg.clear_event_processing(item['id'])
        finally:
            self.queue.task_done()
