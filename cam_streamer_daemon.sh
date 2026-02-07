#!/bin/sh

set -e

if [ -n "${DEBUG}" ]; then
    set -x
fi

script_dir="$(realpath "$(dirname "$0")")"
echo "script_dir: ${script_dir}"

echo "Run cam_streamer.py"
set -x
"${script_dir}/cam_streamer.py" "$@"
