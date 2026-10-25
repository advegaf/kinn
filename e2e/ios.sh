#!/bin/bash
# End to end suite for the Almanac (ios/MotherTongue) in demo mode, on a headless iOS simulator.
#
# Usage, on a Mac with Xcode: e2e/ios.sh
# Uses its own simulator, "Kinn e2e" (made on the first run, override with SIM_NAME). No API keys.
# Builds first, then runs every UI test with the simulator in light mode, then the color scheme
# test in dark mode, then shuts the simulator down. When simq is installed, the simulator part runs
# in its queue (one simulator session at a time on a shared Mac). Each simctl call has a 60 s limit
# and each test run its own limit, so a stuck simulator cannot hold the queue.
# Screenshots go to e2e/out/ios/<run>/. Exit code 1 when a test fails.
set -uo pipefail

cd "$(dirname "$0")/.."
SIM_NAME="${SIM_NAME:-Kinn e2e}"
OUT=e2e/out/ios
DD=ios/build/DD-e2e
BUNDLE=com.hacktx.mothertongue
project=(-project ios/MotherTongue.xcodeproj -scheme MotherTongue -derivedDataPath "$DD")

if [ "${1:-}" != "--session" ]; then
  xcodebuild build-for-testing "${project[@]}" -destination "generic/platform=iOS Simulator" -quiet || exit 1
  rm -rf "$OUT"
  mkdir -p "$OUT"
  if command -v simq >/dev/null; then
    exec simq "$0" --session
  fi
  exec "$0" --session
fi

limit() { local s=$1; shift; perl -e 'alarm shift; exec @ARGV' "$s" "$@"; }
sim() { limit 60 xcrun simctl "$@"; }

udid=$(sim list devices available | grep -F "    $SIM_NAME (" | head -1 | grep -oE '[0-9A-F-]{36}')
if [ -z "$udid" ]; then
  type=$(sim list devicetypes | grep -E '^iPhone [0-9]+ Pro \(' | sort -V | tail -1 | grep -oE 'com\.apple[^)]+')
  udid=$(sim create "$SIM_NAME" "$type")
fi
[ -n "$udid" ] || { echo "No simulator"; exit 1; }
trap 'sim shutdown "$udid" 2>/dev/null' EXIT
sim boot "$udid" 2>/dev/null
# A cold boot on a busy Mac can take more than one 60 s limit.
booted=0
for _ in 1 2 3; do sim bootstatus "$udid" >/dev/null && { booted=1; break; }; done
[ "$booted" -eq 1 ] || { echo "Simulator did not boot"; exit 1; }
sim privacy "$udid" grant microphone "$BUNDLE" 2>/dev/null
sim status_bar "$udid" override --time 9:41 --batteryState charged --batteryLevel 100

failed=0
run() {
  local name=$1 appearance=$2 seconds=$3
  shift 3
  sim ui "$udid" appearance "$appearance"
  limit "$seconds" xcodebuild test-without-building "${project[@]}" -destination "id=$udid" -resultBundlePath "$OUT/$name.xcresult" \
    -test-timeouts-enabled YES -maximum-test-execution-time-allowance 60 "$@" 2>&1 \
    | grep -E "Test Case .*(passed|failed)|error:|Executed" || true
  [ "${PIPESTATUS[0]}" -eq 0 ] || failed=1
  xcrun xcresulttool export attachments --path "$OUT/$name.xcresult" --output-path "$OUT/$name" >/dev/null 2>&1
}

run light light 200
run dark dark 60 -only-testing:MotherTongueUITests/AlmanacTests/testColorSchemeIsFixed
sim ui "$udid" appearance light

if [ "$failed" -ne 0 ]; then
  echo "FAILED. Results and screenshots in $OUT/"
  exit 1
fi
echo "All passed. Screenshots in $OUT/"
