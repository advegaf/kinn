#!/usr/bin/env bash
# H0 smoke test wrapper. If SUPABASE_URL is unset, reads local values from `supabase status`.
# Usage: scripts/smoke.sh path/to/audio.m4a [elder|family]
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -z "${SUPABASE_URL:-}" ]; then
  eval "$(supabase status -o env 2>/dev/null | grep -E '^(API_URL|ANON_KEY)=')"
  export SUPABASE_URL="$API_URL" SUPABASE_ANON_KEY="$ANON_KEY"
fi

exec deno run -A scripts/smoke.ts "$@"
