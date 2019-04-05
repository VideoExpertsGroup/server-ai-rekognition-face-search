import signal

from rekognition_face_search.app import Application

application = None


def signal_handler(sig, frame):
    print('Stopping with signal %s' % sig)
    global application
    if application:
        application.stop()


if __name__ == '__main__':
    # Init application
    application = Application()
    # Init signals handler
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    # Going infinite loop
    application.run()
