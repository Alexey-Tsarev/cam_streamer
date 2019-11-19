# cam_streamer - an easy way to get a low-cost video surveillance system

This is a second edition of a project:  
https://github.com/Alexey-Tsarev/cam_streamer_bash

This is a Python script, which allows you to capture, store,
rotate (remove old data) and restream Web/IP camera streams.  
It works on "any" PC that has Python, GStreamer, FFmpeg.

It tested and works on Raspberry Pi:
Video encoding is forced by the "OpenMAX" Raspberry Pi hardware acceleration:
https://jan.newmarch.name/LinuxSound/Sampled/OpenMAX/

GStreamer is used for video/audio captures and cameras streaming.  

Main config is in the `cfg/main.cfg` file.  
All GStreamer's pipelines are in the `cfg/*.cfg` files and you can easily change them for your needs.

By default GStreamer streams to the Nimble server https://wmspanel.com/nimble (it's free and it works on Raspberry Pi)
via rtmp in flv format (h264 video, aac audio).  
And at the same time the script stores streams using FFmpeg.

Nimble server allows to restream captured data via rtsp, http.  
In this case it's easy to add all capturing streams to the Ivideon service:
https://ivideon.com (you will need the Ivideon Server installed).

There are two options to remove old data:
- keep cameras data less then some desired size
- keep free space where cameras data is located less than some desired size

This is the `top` command output on a Raspberry Pi 2:
~~~
 top - 11:13:33 up  9:39,  3 users,  load average: 1.97, 1.98, 2.00
 Tasks: 166 total,   1 running, 165 sleeping,   0 stopped,   0 zombie
 %Cpu(s): 15.0 us,  3.2 sy,  0.0 ni, 79.2 id,  0.0 wa,  0.0 hi,  2.6 si,  0.0 st
 KiB Mem:    752876 total,   738752 used,    14124 free,    63904 buffers
 KiB Swap:  1023996 total,       24 used,  1023972 free.   521824 cached Mem
 
   PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
  1463 pi        20   0  169104  19416   8204 S  52.0  2.6 303:38.20 gst-launch-1.0 v4l2src device=/dev/v4l/by-id/usb-Sonix_Technology_+
  1450 pi        20   0  163220  13312   5904 S  13.9  1.8 100:37.34 gst-launch-1.0 v4l2src device=/dev/v4l/by-id/usb-046d_09a4_C9469E2+
  1498 pi        20   0  128252  12052   5452 S   7.4  1.6  43:02.80 gst-launch-1.0 v4l2src device=/dev/v4l/by-id/usb-Etron_Technology_+
   906 root      20   0  321476  41548   4572 S   6.5  5.5  35:46.40 /usr/bin/nimble -d --conf-dir=/etc/nimble --log-dir=/var/log/nimbl+
 12213 root      20   0    5252   2380   1952 R   4.6  0.3   0:00.55 top -d 1
...
~~~

In the above example there are 3 USB cameras with the following parameters:
~~~
1463 pid: 1280x720 h264 video + aac audio
1450 pid:  640x480 h264 video + aac audio
1498 pid:  640x480 h264 video, no audio
~~~

Mostly the same for a Raspberry Pi 3:
~~~
$ grep Revision /proc/cpuinfo
Revision        : a22082
~~~

~~~
Tasks: 177 total,   1 running, 176 sleeping,   0 stopped,   0 zombie
%Cpu(s): 12.3 us,  0.8 sy,  0.0 ni, 84.5 id,  0.0 wa,  0.0 hi,  2.4 si,  0.0 st
KiB Mem:    752872 total,   490548 used,   262324 free,    26772 buffers
KiB Swap:  1023996 total,        0 used,  1023996 free.   323548 cached Mem

  PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
 1660 pi        20   0  167892  27348  17668 S  40.3  3.6  22:57.02 gst-launch-1.0 v4l2src device=/dev/v4l/by-id/usb-Sonix_Technology_+
 1695 pi        20   0  126748  19724  14240 S   7.7  2.6   3:51.37 gst-launch-1.0 v4l2src device=/dev/v4l/by-id/usb-Etron_Technology_+
 1647 pi        20   0  163260  22284  15036 S   4.8  3.0   6:10.85 gst-launch-1.0 v4l2src device=/dev/v4l/by-id/usb-046d_09a4_C9469E2+
 1150 root      20   0  314780  39016   7500 S   3.8  5.2   2:07.54 /usr/bin/nimble -d --conf-dir=/etc/nimble --log-dir=/var/log/nimbl+
~~~

## Install
Both: Python 2 and 3 are supported. So just:  
- instead `pip3` you may use `pip2` or just `pip`  
and
- instead `python3` you may use `python2` or just `python`.
~~~
pip3 install -r requirements.txt
python3 cam_streamer.py -log_level INFO -daemon start
tail -f log/main.log
~~~
---

Author: Alexey Tsarev.  
Email:  Tsarev.Alexey at the gmail.com.
