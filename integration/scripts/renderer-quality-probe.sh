#!/bin/bash
set -euo pipefail
export LWE_CLAMPCOMPOSITES=0.85
ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
exec "$ROOT/renderer/scripts/run.sh" "$@"
