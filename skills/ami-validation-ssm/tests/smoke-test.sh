#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash -n "${ROOT}/scripts/launch-and-validate.sh"
"${ROOT}/scripts/launch-and-validate.sh" --help >/dev/null
