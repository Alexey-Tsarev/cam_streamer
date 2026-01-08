#!/bin/sh

set -e

if [ -n "${DEBUG}" ]; then
    set -x
fi

script_dir="$(realpath "$(dirname "$0")")"
echo "script_dir: ${script_dir}"

rm -f "${script_dir}/pid/main.pid"

virtualenv="${script_dir}/.virtualenv/bin/activate"
echo "Activate Python virtualenv: ${virtualenv}"

# shellcheck source=.virtualenv/bin/activate
. "${virtualenv}"

echo "Run cam_streamer.py"
set -x
exec "${script_dir}/cam_streamer.py" "$@"
