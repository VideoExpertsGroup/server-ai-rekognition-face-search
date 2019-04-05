import boto3
from botocore.exceptions import ClientError


class AWSClientBadConfig(Exception):
    pass


class AWSClient:
    """
    AWS Rekognition client.
    Just wraps some boto3 requests.
    """
    def __init__(self, collection_id: str, access_key: str, secret_key: str):
        self.collection_id = collection_id
        if not all((self.collection_id, access_key, secret_key)):
            raise AWSClientBadConfig()

        self.rek = boto3.client('rekognition',
                                region_name='us-east-1',
                                aws_access_key_id=access_key,
                                aws_secret_access_key=secret_key)

        # ensure collection exists
        try:
            self.create_collection()
        except ClientError as ex:
            if ex.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise

    def create_collection(self):
        return self.rek.create_collection(CollectionId=self.collection_id)

    def delete_collection(self):
        return self.rek.delete_collection(CollectionId=self.collection_id)

    def search_face(self, image):
        return self.rek.search_faces_by_image(
            CollectionId=self.collection_id,
            Image={'Bytes': image},
            FaceMatchThreshold=0.7
        )

    def index_faces(self, image):
        return self.rek.index_faces(
            CollectionId=self.collection_id,
            Image={'Bytes': image},
        )
