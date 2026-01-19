#!/bin/sh

set -x

name=shEl720
IP="${IP:-${name}}"

    exec gst-launch-1.0 \
        rtspsrc location="rtsp://${IP}:554/user=admin_password=tlJwpbo6_channel=1_stream=0.sdp?real_stream" latency=0 name=src \
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
            ! rtppcmadepay \
            ! alawdec \
            ! audioconvert \
            ! audioresample \
            ! "audio/x-raw,rate=22050,channels=1" \
            ! avenc_aac bitrate=24000 \
            ! aacparse \
            ! queue max-size-buffers=10 \
            ! mux.audio \
        flvmux name=mux \
            ! rtmpsink location="rtmp://127.0.0.1/app/${name}"
