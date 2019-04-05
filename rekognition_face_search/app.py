import os
from queue import Queue
from threading import Thread

from .aws_client import AWSClient, AWSClientBadConfig
from .poller import PollingImageSource
from .vxg_client import VXGClient, VXGClientBadConfig
from .web import WebApplication
from .worker import Worker

WEB_UI_PORT = 8080
WORKERS_COUNT = 20
QUEUE_MAX_SIZE = 5 * WORKERS_COUNT
WORKERS_GRACE_STOP_TIMEOUT = 5


class Application:
    def __init__(self):
        self.server_uri = os.environ.get('SERVER_URI', None)
        self.token = os.environ.get('TOKEN', None)
        self.collection = os.environ.get('COLLECTION_ID', None)
        self.access_key = os.environ.get('ACCESS_KEY', None)
        self.secret_key = os.environ.get('SECRET_KEY', None)

        self.queue = Queue(maxsize=QUEUE_MAX_SIZE)
        self.web = WebApplication(self)
        # Other components must be initialized at the runtime, because settings can be changed or even missing
        self.source = None
        self.source_thread = None
        self.workers = None
        self.worker_threads = None

    def run(self):
        print('Starting..')
        self.start_source_and_workers()
        # This one runs forever
        self.web.routine(WEB_UI_PORT)
        print('Finished')

    def stop(self):
        self.stop_source_and_workers()
        print('Stopping web..')
        self.web.stop()

    def start_source_and_workers(self):
        try:
            self.source = PollingImageSource(VXGClient(server_uri=self.server_uri, token=self.token), self.queue)
            self.source_thread = Thread(name='Source', target=self.source.routine)
            self.source_thread.start()
            print('Polling VXG Server at "%s"' % self.server_uri)
        except VXGClientBadConfig:
            self.source = None
            self.source_thread = None
            print('Polling routine is not started due to bad configuration. You should set SERVER_URI and TOKEN env '
                  'vars or use web config page')

        try:
            self.workers = [
                Worker(self.queue,
                       AWSClient(collection_id=self.collection, access_key=self.access_key, secret_key=self.secret_key),
                       VXGClient(server_uri=self.server_uri, token=self.token))
                for _ in range(WORKERS_COUNT)
            ]
            self.worker_threads = [Thread(name='Worker %d' % idx, target=self.workers[idx].routine)
                                   for idx in range(WORKERS_COUNT)]
            for worker_thread in self.worker_threads:
                worker_thread.start()
            print('Using AWS Rekognition collection "%s"' % self.collection)
        except (AWSClientBadConfig, VXGClientBadConfig):
            self.workers = None
            self.worker_threads = None
            print('Worker routines are not started due to bad configuration. You should set SERVER_URI, TOKEN, '
                  'COLLECTION_ID, ACCESS_KEY and SECRET_KEY  env vars or use web config page')

    def stop_source_and_workers(self):
        print('Setting stop events')
        if self.workers:
            for worker in self.workers:
                worker.stop()
        if self.source:
            self.source.stop()

        print('Waiting for threads..')
        if self.worker_threads:
            for worker_thread in self.worker_threads:
                worker_thread.join(timeout=WORKERS_GRACE_STOP_TIMEOUT)
        if self.source_thread:
            self.source_thread.join(timeout=WORKERS_GRACE_STOP_TIMEOUT)

        self.workers = None
        self.worker_threads = None
        self.source = None
        self.source_thread = None
        print('Threads are stopped')

    def restart_source_and_workers(self):
        self.stop_source_and_workers()
        self.start_source_and_workers()
