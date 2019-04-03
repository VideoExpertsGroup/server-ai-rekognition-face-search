import os
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
    try:
        application = Application(server_uri=os.environ['SERVER_URI'],
                                  license_key=os.environ['LICENSE_KEY'],
                                  rekognition_collection_id=os.environ['COLLECTION_ID'],
                                  aws_access_key=os.environ['ACCESS_KEY'],
                                  aws_secret_key=os.environ['SECRET_KEY'])
    except KeyError as ex:
        print('Missing env variable %s, for now setting environment variables is the only way to configure this '
              'service' % ex)
        exit(1)
    # Init signals handler
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    # Going infinite loop
    application.run()
