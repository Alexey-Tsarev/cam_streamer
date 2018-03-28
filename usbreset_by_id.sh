#!/usr/bin/env bash

USAGE="Usage:
${0} USB_DEVICE_AT_DEV_FILE_SYSTEM
(See devices in /dev/v4l/...)"

if [ -n "${1}" ]; then
    UDEV_DATA="$(udevadm info -a --name ${1})"
    BUS="$(echo "${UDEV_DATA}" | grep -m 1 busnum | cut -d '"' -f 2)"
    DEV="$(echo "${UDEV_DATA}" | grep -m 1 devnum | cut -d '"' -f 2)"

    if [ -n "${BUS}" ] && [ -n "${DEV}" ]; then
        ./usbreset_by_bus_dev.sh "${BUS}" "${DEV}"
    else
        echo "Failed to find bus and/or dev for device: ${1}"
    fi
else
    echo "${USAGE}"
    exit 1
fi
