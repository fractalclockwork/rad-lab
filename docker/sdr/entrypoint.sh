#!/usr/bin/env bash
set -euo pipefail
# Keep PATH predictable inside the container.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"
exec "$@"
