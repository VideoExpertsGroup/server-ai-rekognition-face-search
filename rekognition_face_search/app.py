from queue import Queue
from threading import Thread

from .aws_client import AWSClient
from .poller import PollingImageSource
from .vxg_client import VXGClient
from .worker import Worker

WORKERS_COUNT = 20
QUEUE_MAX_SIZE = 5 * WORKERS_COUNT
WORKERS_GRACE_STOP_TIMEOUT = 5


class Application:
    def __init__(self, server_uri: str,
                 license_key: str,
                 rekognition_collection_id: str,
                 aws_access_key: str,
                 aws_secret_key: str):
        self.server_uri = server_uri
        self.rek_coll_id = rekognition_collection_id
        self.queue = Queue(maxsize=QUEUE_MAX_SIZE)
        self.source = PollingImageSource(VXGClient(server_uri=self.server_uri, license_key=license_key), self.queue)
        self.workers = [
            Worker(self.queue,
                   AWSClient(collection_id=self.rek_coll_id, access_key=aws_access_key, secret_key=aws_secret_key),
                   VXGClient(server_uri=self.server_uri, license_key=license_key))
            for _ in range(WORKERS_COUNT)
        ]
        self.worker_threads = [Thread(name='Worker %d' % idx, target=self.workers[idx].routine)
                               for idx in range(WORKERS_COUNT)]

    def run(self):
        print('Starting..')
        for worker_thread in self.worker_threads:
            worker_thread.start()
        # This one runs forever
        print('Polling "%s" and use AWS Rekognition collection "%s"' % (self.server_uri, self.rek_coll_id))
        self.source.routine()
        print('Exit')

    def stop(self):
        print('Set stop events')
        Worker.NEED_STOP.set()
        self.source.NEED_STOP.set()
        print('Waiting for threads..')
        for worker_thread in self.worker_threads:
            worker_thread.join(timeout=WORKERS_GRACE_STOP_TIMEOUT)
        print('Stopped')
