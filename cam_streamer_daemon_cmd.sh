#!/bin/sh

#set -x
set -e

if [ -z "$1" ]; then
    echo "Fatal error, use: $0 [start|stop|restart]"
    exit 1
fi

if [ -z "$2" ]; then
    log_level="INFO"
else
    log_level="$2"
fi

script_dir="$(realpath "$(dirname "$0")")"

cd "${script_dir}"
. .venv/bin/activate

python3 cam_streamer.py -log_level "${log_level}" -daemon "$1"
