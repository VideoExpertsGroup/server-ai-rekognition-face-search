import json
from urllib.parse import urlencode

import requests


class VXGClient:
    """
    Wrapper for VXG Server Web API.
    """
    TAG_PROCESSING = 'rek_face_search_processing'
    TAG_HAS_FACE = 'rek_face_search_processed_has_face'
    TAG_NO_FACE = 'rek_face_search_processed_no_face'
    TAG_ERROR = 'rek_face_search_error'
    TAG_FACE_FMT = 'rek_face_search_faceid_%s'

    SERVICE_TAGS = (TAG_PROCESSING, TAG_HAS_FACE, TAG_NO_FACE, TAG_ERROR)

    ENDPOINTS = {
        'events': 'v2/storage/events/',
        'event': 'v2/storage/events/%(id)d/',
        'event_metas': 'v2/storage/events/%(id)d/meta/',
        'event_meta': 'v2/storage/events/%(id)d/meta/%(tag)s/'
    }

    def __init__(self, server_uri: str, token: str):
        self.server_uri = server_uri
        self.token = token

    def _get_url(self, typ: str, params: dict = None, query: list = None) -> str:
        if not params:
            params = {}

        if not query:
            query = []

        query.append(('token', self.token))
        return '%s/api/%s?%s' % (self.server_uri, self.ENDPOINTS[typ] % params, urlencode(query, safe=','))

    def get_unprocessed_events(self, limit: int) -> (list, int):
        """
        Get batch of unprocessed events
        :param limit: limit the results
        :return: list of events and total number of unprocessed events on the server
        """
        resp = requests.get(self._get_url('events', query=[
            ('type', 'facedetection'),
            ('meta_not', ','.join(self.SERVICE_TAGS)),
            ('limit', limit)
        ]))
        resp.raise_for_status()
        resp_json = resp.json()
        return resp_json['objects'], resp_json['meta']['total_count']

    def set_event_processing(self, event_id: int):
        """
        Set the "processing" tag to event, indicating that we're going to process it
        :param event_id: event ID from VXG Server
        """
        resp = requests.post(self._get_url('event_metas', params={'id': event_id}),
                             json={'data': '', 'tag': self.TAG_PROCESSING})
        resp.raise_for_status()

    def clear_event_processing(self, event_id: int):
        """
        Delete "Processing" tag from event
        :param event_id: event ID from VXG Server
        """
        resp = requests.delete(self._get_url('event_meta', params={'id': event_id, 'tag': self.TAG_PROCESSING}))
        resp.raise_for_status()

    def set_event_processed(self, event_id: int, faces: list):
        """
        Set "processed" tag to the event and also set tags with processing results
        :param event_id: event ID from VXG Server
        :param faces: list of results as dicts with essential key 'FaceId'
        """
        if faces:
            resp = requests.post(self._get_url('event_metas', params={'id': event_id}),
                                 json={'data': '', 'tag': self.TAG_HAS_FACE})
            resp.raise_for_status()
            for face in faces:
                face_id = face.pop('FaceId')
                resp = requests.post(self._get_url('event_metas', params={'id': event_id}),
                                     json={'data': json.dumps(face), 'tag': self.TAG_FACE_FMT % face_id})
                resp.raise_for_status()
        else:
            resp = requests.post(self._get_url('event_metas', params={'id': event_id}),
                                 json={'data': '', 'tag': self.TAG_NO_FACE})
            resp.raise_for_status()

    def set_event_processed_error(self, event_id: int, message: str):
        """
        Set "processed_with_error" tag
        :param event_id: event ID from VXG Server
        :param message: short description what were wrong
        :return:
        """
        resp = requests.post(self._get_url('event_metas', params={'id': event_id}),
                             json={'data': message, 'tag': self.TAG_ERROR})
        resp.raise_for_status()

    def get_event_details(self, event_id: int) -> dict:
        """
        Used only for testing
        :param event_id:
        :return:
        """
        resp = requests.get(self._get_url('event', params={'id': event_id}, query=[('include_meta', 'true')]))
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
            resp = requests.delete(self._get_url('event_meta', params={'id': event_id, 'tag': self.TAG_HAS_FACE}))
            resp.raise_for_status()
            for face in faces:
                resp = requests.delete(self._get_url('event_meta', params={'id': event_id,
                                                                           'tag': self.TAG_FACE_FMT % face['FaceId']}))
                resp.raise_for_status()
        else:
            resp = requests.delete(self._get_url('event_meta', params={'id': event_id, 'tag': self.TAG_NO_FACE}))
            resp.raise_for_status()
