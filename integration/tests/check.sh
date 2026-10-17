#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
"$root/renderer/tests/check.sh"
"$root/gnome/tests/check.sh"
if [ "${1:-}" = --integration ]; then
    /usr/bin/python3 "$root/integration/tests/check-pointer-runtime.py"
    /usr/bin/python3 "$root/integration/tests/check-gnome-integration.py"
fi
