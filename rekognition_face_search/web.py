import asyncio

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application as TornadoApplication
from tornado.testing import bind_unused_port


class WebApplication(TornadoApplication):
    def __init__(self, app):
        super(WebApplication, self).__init__([
            (r"/settings/", SettingsHandler),
            (r"/status/", StatusHandler),
        ])
        self.app = app
        self.loop = None
        self.port = None  # Actual port that we're running
        self.apply_in_progress = False

    @staticmethod
    def _ensure_event_loop():
        try:
            _ = asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

    def routine(self, port: int = None):
        self._ensure_event_loop()
        if port is None:
            sock, port = bind_unused_port()
            http_server = HTTPServer(self)
            http_server.add_sockets([sock])
        else:
            self.listen(port)
        self.port = port
        self.loop = IOLoop().current()
        self.loop.start()

    def stop(self):
        if self.loop:
            self.loop.stop()


class SettingsHandler(RequestHandler):
    async def get(self):
        await self.render('templates/settings.html',
                          server_uri=self.application.app.server_uri or '',
                          token=self.application.app.token or '',
                          collection=self.application.app.collection or '',
                          access_key=self.application.app.access_key or '',
                          secret_key=self.application.app.secret_key or '',
                          apply_in_progress=self.application.apply_in_progress)

    async def post(self):
        if not self.application.apply_in_progress:
            self.application.app.server_uri = self.get_argument('server_uri')
            self.application.app.token = self.get_argument('token')
            self.application.app.collection = self.get_argument('collection')
            self.application.app.access_key = self.get_argument('access_key')
            self.application.app.secret_key = self.get_argument('secret_key')
            self.application.apply_in_progress = True
            await self.application.loop.run_in_executor(func=self.application.app.restart_source_and_workers,
                                                        executor=None)
            self.application.apply_in_progress = False
        await self.render('templates/settings.html',
                          server_uri=self.application.app.server_uri or '',
                          token=self.application.app.token or '',
                          collection=self.application.app.collection or '',
                          access_key=self.application.app.access_key or '',
                          secret_key=self.application.app.secret_key or '',
                          apply_in_progress=self.application.apply_in_progress)


class StatusHandler(RequestHandler):
    async def get(self):
        self.write({'source_running': self.application.app.source is not None,
                    'workers_running': self.application.app.workers is not None,
                    'queue_size': self.application.app.queue.qsize()})
