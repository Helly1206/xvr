FROM python:3.12-slim-bookworm

COPY ./docker/ffmpeg /usr/bin

WORKDIR /data
WORKDIR /data/config
WORKDIR /data/log
WORKDIR /cameras
WORKDIR /app

COPY ./docker/requirements.txt .
RUN pip install -r requirements.txt
RUN rm -f requirements.txt

COPY ./opt/xvr /app

EXPOSE 8081

CMD ["python", "./dxvr"]