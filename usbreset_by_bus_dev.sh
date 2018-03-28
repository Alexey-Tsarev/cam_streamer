#!/usr/bin/env bash

USAGE="Usage:
${0} USB_BUS USB_DEV
(See an output of the 'lsusb' command)"

if [ -n "${1}" ] && [ -n "${2}" ]; then
    ./usbreset /dev/bus/usb/*${1}/*${2}
else
    echo "${USAGE}"
    exit 1
fi
