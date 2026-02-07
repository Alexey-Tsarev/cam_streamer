#!/bin/bash

set -x

name=cAm3
IP="${IP:-${name}}"

    exec gst-launch-1.0 \
        souphttpsrc location=http://${IP}:8080/video is-live=true do-timestamp=true \
            ! multipartdemux \
            ! image/jpeg,framerate=2/1 \
            ! jpegdec \
            ! videorate \
            ! video/x-raw,framerate=2/1 \
            ! clockoverlay time-format="${name} %Y-%m-%d %H:%M:%S.%L" xpad=0 ypad=16 font-desc="Lucida Console Bold 22" auto-resize=0 shaded-background=1 \
            ! timeoverlay halignment=left valignment=bottom text="${name}" shaded-background=true font-desc="Sans, 8" \
            ! videoconvert \
            ! openh264enc \
            ! "video/x-h264,level=(string)4" \
            ! h264parse \
            ! queue max-size-buffers=10 \
            ! mux.video \
        souphttpsrc location=http://${IP}:8080/audio.wav is-live=true do-timestamp=true \
            ! wavparse \
            ! audioconvert \
            ! rgvolume pre-amp=6.0 headroom=10.0 \
            ! rglimiter \
            ! audioresample \
            ! "audio/x-raw,rate=22050,channels=1" \
            ! audioconvert \
            ! voaacenc bitrate=24000 \
            ! aacparse \
            ! queue max-size-buffers=10 \
            ! mux.audio \
        flvmux name=mux \
            ! rtmpsink location="rtmp://127.0.0.1/app/${name}"

# ffplay http://127.0.0.1:3333/app/cAm3/master.m3u8
# ffplay http://127.0.0.1:3333/app/cam3/master.m3u8
