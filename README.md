# cam_streamer - an easy way to get a low-cost video surveillance system

This is a third edition of a project:  
https://github.com/Alexey-Tsarev/cam_streamer/tree/dev

This is a Python script, which allows you to capture, store,
rotate (remove old data) and restream Web/IP camera streams.  
It works on "any" PC that has Python, GStreamer.

It tested and works on Raspberry Pi:
Video encoding is forced by the "OpenMAX" Raspberry Pi hardware acceleration:
https://jan.newmarch.name/LinuxSound/Sampled/OpenMAX/

GStreamer is used for video/audio captures and cameras streaming.

Main config is in the `cfg/main.cfg` file.  
All GStreamer's pipelines are in the `cfg/*.cfg` files, and you can easily change them for your needs.

By default, Python script streams to OvenMediaEngine https://github.com/AirenSoft/OvenMediaEngine
via rtmp in flv format (h264 video, aac audio). And at the same time the OvenMediaEngine stores streams.  
So the script does not save streamed data, instead of previous version: https://github.com/Alexey-Tsarev/cam_streamer/tree/dev

## Install
To use this project, you need [uv](https://docs.astral.sh/uv/getting-started/installation/) installed.

## Run
~~~
./cam_streamer.py --help
usage: cam_streamer.py [-h] [-daemon {start,stop,restart}] [-log_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]

options:
  -h, --help            show this help message and exit
  -daemon {start,stop,restart}
                        Daemon mode startup options
  -log_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Override config log_level
~~~

~~~
./cam_streamer_daemon.sh -daemon restart -log_level INFO
script_dir: /Users/atsarev/devv/cam_streamer
Run cam_streamer.py
+ /Users/atsarev/devv/cam_streamer/cam_streamer.py -daemon restart -log_level INFO
~~~

## Logs
~~~
tail -f log/main.log
~~~

## Docker
Image: https://hub.docker.com/r/alexeytsarev/cam_streamer
```
docker run --rm alexeytsarev/cam_streamer
```
or get this project: https://github.com/Alexey-Tsarev/dockered and run:
```
cd images
docker compose up ome cam_streamer
```
---

Good luck,  
*Author*: Alexey Tsarev  
*Email*:  Tsarev.Alexey at gmail.com
