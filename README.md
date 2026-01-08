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
Python 3 only.

Create a `virtualenv` (not required and depends on you):
~~~
python3 -m venv .virtualenv
# virtualenv .virtualenv
. .virtualenv/bin/activate
~~~

Install dependencies:
~~~
pip3 install -r requirements.txt
~~~

Run `virtualenv` through wrapper:
~~~
./cam_streamer_daemon.sh restart INFO
~~~

Logs:
~~~
tail -f log/main.log
~~~

## Docker
Image: https://hub.docker.com/r/alexeytsarev/cam_streamer
```
docker run --rm alexeytsarev/cam_streamer
```
---

Good luck,  
*Author*: Alexey Tsarev  
*Email*:  Tsarev.Alexey at gmail.com
