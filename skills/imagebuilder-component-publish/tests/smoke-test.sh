#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash -n "${ROOT}/scripts/publish-component.sh"
"${ROOT}/scripts/publish-component.sh" --help >/dev/null
