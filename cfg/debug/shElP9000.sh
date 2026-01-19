#!/bin/sh

set -x

name=shElP9000
IP="${IP:-${name}}"

    exec gst-launch-1.0 \
        rtspsrc location="rtsp://${IP}:8080/h264_pcm.sdp" latency=0 name=src \
        src. \
            ! queue max-size-buffers=10 \
            ! capsfilter caps="application/x-rtp,media=video" \
            ! rtph264depay \
            ! h264parse \
            ! queue max-size-buffers=10 \
            ! mux.video \
        src. \
            ! queue max-size-buffers=10 \
            ! capsfilter caps="application/x-rtp,media=audio" \
            ! decodebin \
            ! audioconvert \
            ! audioresample \
            ! "audio/x-raw,rate=22050,channels=1" \
            ! avenc_aac bitrate=24000 \
            ! aacparse \
            ! queue max-size-buffers=10 \
            ! mux.audio \
        flvmux name=mux \
            ! rtmpsink location="rtmp://127.0.0.1/app/${name}"
