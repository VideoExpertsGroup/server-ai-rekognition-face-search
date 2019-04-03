from threading import Thread, Event
from time import sleep
from queue import Queue, Full
import traceback

from .vxg_client import VXGClient


class PollingImageSource:
    """
    Periodically polls VXG Server for images that are marked by cameras as having some face.
    Gets storage URL and event ID for that images and passes them to processing queue.
    Those events are marked with "processing" meta tag.
    """
    MAX_EVENT_BATCH = 20
    POLL_INTERVAL = 0.5

    NEED_STOP = Event()

    def __init__(self, vxg_client: VXGClient, queue: Queue):
        self.vxg_client = vxg_client
        self.queue = queue

    def routine(self):
        """
        Main routine
        """
        timeout = self.POLL_INTERVAL
        while not self.NEED_STOP.wait(timeout=timeout):
            try:
                try:
                    more = self.poll_events()
                except StopIteration:
                    break
                timeout = 0 if more else self.POLL_INTERVAL
            except Exception as ex:
                print('Unexpected exception at PollingImageSource.routine: %s\n%s' % (ex, traceback.format_exc()))
                sleep(1)

    def poll_events(self) -> bool:
        """
        Single run of the main routine
        :raises StopIteration: when user asked us to stop
        :return: Is there more events at the server
        """
        # TODO: first run should grab all unprocessed events too
        # TODO: try to switch to remembering last event ID, not by relying to "processing" tag
        events, more = self.get_events()
        for event in events:
            url = event.get('thumb', {}).get('url', None)
            if not url:
                self.vxg_client.set_event_processed_error(event['id'], 'no_image')
            else:
                while True:
                    try:
                        self.queue.put({
                            'id': event['id'],
                            'url': url,
                        }, timeout=1)
                        break
                    except Full:
                        if self.NEED_STOP.is_set():
                            raise StopIteration()
                self.vxg_client.set_event_processing(event['id'])

        return more

    def get_events(self) -> (list, bool):
        """
        Get batch of events from VXG Server
        :return: Batch of events and bool indicating is there more events at the server
        """
        events, total = self.vxg_client.get_unprocessed_events(limit=self.MAX_EVENT_BATCH)
        return events, total > self.MAX_EVENT_BATCH
