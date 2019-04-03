FROM python:3.7-alpine
WORKDIR /srv/rekognition_face_search
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt
COPY . .
CMD ["python3", "run_sync.py"]