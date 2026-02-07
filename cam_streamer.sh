#!/bin/sh

set -e

if [ -n "${DEBUG}" ]; then
    set -x
fi

script_dir="$(realpath "$(dirname "$0")")"
echo "script_dir: ${script_dir}"

rm -f "${script_dir}/pid/main.pid"

echo "Run cam_streamer.py"
set -x
exec "${script_dir}/cam_streamer.py" "$@"
