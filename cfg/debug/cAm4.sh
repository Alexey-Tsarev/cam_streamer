#!/bin/bash

set -x

name=cAm4
IP="${IP:-${name}}"


    exec gst-launch-1.0 \
        rtspsrc location="rtsp://${IP}:8080/h264_pcm.sdp" latency=0 name=src \
        src. \
            ! queue max-size-buffers=10 \
            ! capsfilter caps="application/x-rtp,media=video" \
            ! rtph264depay \
            ! queue max-size-buffers=10 \
            ! mux. \
        src. \
            ! queue max-size-buffers=10 \
            ! capsfilter caps="application/x-rtp,media=audio" \
            ! decodebin \
            ! audioconvert \
            ! audioresample \
            ! audio/x-raw,rate=8000,channels=1 \
            ! queue max-size-buffers=10 \
            ! audioconvert \
            ! avenc_aac bitrate=8000 \
            ! aacparse \
            ! queue max-size-buffers=10 \
            ! mux. \
        flvmux name=mux \
            ! rtmpsink location=location="rtmp://127.0.0.1/app/${name}"
