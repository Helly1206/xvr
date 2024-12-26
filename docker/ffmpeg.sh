#!/usr/bin/bash

echo Installing ffmpeg

mkdir install
cd install
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar -xf ffmpeg-release-amd64-static.tar.xz
FFMPEG="$(find . -name ffmpeg)"
cp $FFMPEG ../
cd ../
rm -rf install

echo ffmpeg install done