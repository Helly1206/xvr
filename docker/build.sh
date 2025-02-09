#!/usr/bin/bash

APP_NAME="xvr"
VERSION="0.8.2"

./ffmpeg.sh
docker build --no-cache -t $APP_NAME:v$VERSION -f ./Dockerfile ..
rm -f ./ffmpeg