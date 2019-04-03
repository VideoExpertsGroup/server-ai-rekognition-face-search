import json
import requests


class VXGClient:
    """
    Wrapper for VXG Server Web API.
    """
    TAG_PROCESSING = 'rek_face_search_processing'
    TAG_HAS_FACE = 'rek_face_search_processed_has_face'
    TAG_NO_FACE = 'rek_face_search_processed_no_face'
    TAG_FACE_FMT = 'rek_face_search_faceid_%s'
    TAG_ERROR = 'rek_face_search_error'

    ENDPOINTS = {
        'get_events_unprocessed': 'v2/storage/events/?type=facedetection&meta_not=%s,%s,%s,%s&limit=%%(limit)d' % (
            TAG_PROCESSING, TAG_HAS_FACE, TAG_NO_FACE, TAG_ERROR),
        'get_event_details': 'v2/storage/events/%(id)d/?include_meta=true',
        'event_processing': 'v2/storage/events/%%(id)d/meta/%s/' % TAG_PROCESSING,
        'event_processed_has_face': 'v2/storage/events/%%(id)d/meta/%s/' % TAG_HAS_FACE,
        'event_processed_no_face': 'v2/storage/events/%%(id)d/meta/%s/' % TAG_NO_FACE,
        'event_face_fmt': 'v2/storage/events/%%(id)d/meta/%s%%(face_id)s/' % (TAG_FACE_FMT % ''),
        'event_meta': 'v2/storage/events/%(id)d/meta/'
    }

    def __init__(self, server_uri: str, license_key: str):
        self.server_uri = server_uri
        self.l_key = license_key
        self._auth = {'Authorization': 'LKey %s' % self.l_key}

    def _get_url(self, typ, **params) -> str:
        return '%s/api/%s' % (self.server_uri, self.ENDPOINTS[typ] % params)

    def get_unprocessed_events(self, limit: int) -> (list, int):
        """
        Get batch of unprocessed events
        :param limit: limit the results
        :return: list of events and total number of unprocessed events on the server
        """
        resp = requests.get(self._get_url('get_events_unprocessed', limit=limit), headers=self._auth)
        resp.raise_for_status()
        resp_json = resp.json()
        return resp_json['objects'], resp_json['meta']['total_count']

    def set_event_processing(self, event_id: int):
        """
        Set the "processing" tag to event, indicating that we're going to process it
        :param event_id: event ID from VXG Server
        """
        resp = requests.post(self._get_url('event_meta', id=event_id), headers=self._auth,
                             json={'data': '', 'tag': self.TAG_PROCESSING})
        resp.raise_for_status()

    def clear_event_processing(self, event_id: int):
        """
        Delete "Processing" tag from event
        :param event_id: event ID from VXG Server
        """
        resp = requests.delete(self._get_url('event_processing', id=event_id), headers=self._auth)
        resp.raise_for_status()

    def set_event_processed(self, event_id: int, faces: list):
        """
        Set "processed" tag to the event and also set tags with processing results
        :param event_id: event ID from VXG Server
        :param faces: list of results as dicts with essential key 'FaceId'
        """
        if faces:
            resp = requests.post(self._get_url('event_meta', id=event_id), headers=self._auth,
                                 json={'data': '', 'tag': self.TAG_HAS_FACE})
            resp.raise_for_status()
            for face in faces:
                resp = requests.post(self._get_url('event_meta', id=event_id), headers=self._auth,
                                     json={'data': json.dumps(face), 'tag': self.TAG_FACE_FMT % face['FaceId']})
                resp.raise_for_status()
        else:
            resp = requests.post(self._get_url('event_meta', id=event_id), headers=self._auth,
                                 json={'data': '', 'tag': self.TAG_NO_FACE})
            resp.raise_for_status()

    def set_event_processed_error(self, event_id: int, message: str):
        """
        Set "processed_with_error" tag
        :param event_id: event ID from VXG Server
        :param message: short description what were wrong
        :return:
        """
        resp = requests.post(self._get_url('event_meta', id=event_id), headers=self._auth,
                             json={'data': message, 'tag': self.TAG_ERROR})
        resp.raise_for_status()

    def get_event_details(self, event_id: int) -> dict:
        """
        Used only for testing
        :param event_id:
        :return:
        """
        resp = requests.get(self._get_url('get_event_details', id=event_id), headers=self._auth)
        resp.raise_for_status()
        resp_json = resp.json()
        return resp_json

    def clear_event_processed(self, event_id: int, faces: list):
        """
        Used only for testing
        :param event_id:
        :param faces:
        """
        if faces:
            resp = requests.delete(self._get_url('event_processed_has_face', id=event_id), headers=self._auth)
            resp.raise_for_status()
            for face in faces:
                resp = requests.delete(self._get_url('event_face_fmt', id=event_id, face_id=face['FaceId']),
                                       headers=self._auth)
                resp.raise_for_status()
        else:
            resp = requests.delete(self._get_url('event_processed_no_face', id=event_id), headers=self._auth)
            resp.raise_for_status()
