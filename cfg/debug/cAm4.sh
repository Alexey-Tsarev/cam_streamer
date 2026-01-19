#!/bin/bash

set -x

name=cAm4
IP="${IP:-${name}}"


    exec gst-launch-1.0 \
        rtspsrc location="rtsp://${IP}:8080/h264_pcm.sdp" latency=0 name=src \
        src. \
            ! queue \
            ! capsfilter caps="application/x-rtp,media=video" \
            ! rtph264depay \
            ! queue \
            ! mux. \
        src. \
            ! queue \
            ! capsfilter caps="application/x-rtp,media=audio" \
            ! decodebin \
            ! audioconvert \
            ! audioresample \
            ! audio/x-raw,rate=8000,channels=1 \
            ! queue \
            ! audioconvert \
            ! avenc_aac bitrate=8000 \
            ! aacparse \
            ! queue \
            ! mux. \
        flvmux name=mux \
            ! rtmpsink location=location="rtmp://127.0.0.1/app/${name}"
