#!/usr/bin/env bash

USAGE="Usage:
${0} USB_DEVICE_NAME
(See an output of the 'lsusb' command)"

if [ -n "${1}" ]; then
    USB_LINE="$(lsusb | grep "${1}")"

    if [ -n "${USB_LINE}" ]; then
        echo "Device '${1}' found. USB line:
${USB_LINE}"

        USB_LINE_AR=(${USB_LINE})
        BUS="${USB_LINE_AR[1]}"
        DEV="${USB_LINE_AR[3]/:/}"
    else
        echo "Device not found: ${1}"
    fi

    if [ -n "${BUS}" ] && [ -n "${DEV}" ]; then
        ./usbreset_by_bus_dev.sh "${BUS}" "${DEV}"
    else
        echo "Failed to find bus and/or dev for device: ${1}"
    fi
else
    echo "${USAGE}"
    exit 1
fi
