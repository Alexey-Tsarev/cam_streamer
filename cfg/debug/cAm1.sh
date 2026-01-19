#!/bin/bash

set -x

name=cAm1

    exec gst-launch-1.0 \
        v4l2src device=`ls /dev/v4l/by-id/usb-046d_09a4_C9469E20-* | head -n 1` do-timestamp=true \
            ! videorate \
            ! "video/x-raw,framerate=5/1" \
            ! clockoverlay time-format="${name} %Y-%m-%d %H:%M:%S" xpad=0 ypad=0 font-desc="Lucida Console Bold 24" auto-resize=0 shaded-background=1 \
            ! timeoverlay halignment=left valignment=bottom text="${name}" shaded-background=true font-desc="Sans, 8" \
            ! videoconvert \
            ! x264enc tune=zerolatency speed-preset=veryfast bitrate=500 key-int-max=10 \
            ! "video/x-h264,profile=baseline" \
            ! h264parse \
            ! queue max-size-buffers=10 \
            ! mux.video \
        alsasrc device=hw:`readlink /dev/snd/by-id/usb-046d_09a4_C9469E20-* | sed 's/[^0-9]*//g'` do-timestamp=true provide-clock=false \
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
            ! rtmpsink location="rtmp://10.1.7.2/app/${name}"
