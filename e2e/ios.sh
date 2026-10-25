#!/bin/bash
# End to end suite for the Almanac (ios/MotherTongue) in demo mode, on a headless iOS simulator.
#
# Usage, on a Mac with Xcode: e2e/ios.sh
# Uses its own simulator, "Kinn e2e" (made on the first run, override with SIM_NAME). No API keys.
# Builds first, then runs every UI test with the simulator in light mode, then the color scheme
# test in dark mode, then shuts the simulator down. When simq is installed, the simulator part runs
# in its queue (one simulator session at a time on a shared Mac). Each simctl call has a 60 s limit
# (the boot 3 min), each test run has its own limit, and the whole session stops before 5 min, so a
# stuck simulator cannot hold the queue.
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

# The whole session stays under 5 min (simq rule). The last 30 s are kept for the shutdown.
WORK_END=255
left() { echo $((WORK_END - SECONDS)); }
limit() {
  local s=$1 l
  shift
  l=$(left)
  [ "$l" -lt "$s" ] && s=$l
  [ "$s" -gt 0 ] || { echo "Session time is used up: $*" >&2; return 124; }
  perl -e 'alarm shift; exec @ARGV' "$s" "$@"
}
sim() { limit 60 xcrun simctl "$@"; }

udid=$(sim list devices available | grep -F "    $SIM_NAME (" | head -1 | grep -oE '[0-9A-F-]{36}')
if [ -z "$udid" ]; then
  type=$(sim list devicetypes | grep -E '^iPhone [0-9]+ Pro \(' | sort -V | tail -1 | grep -oE 'com\.apple[^)]+')
  udid=$(sim create "$SIM_NAME" "$type")
fi
[ -n "$udid" ] || { echo "No simulator"; exit 1; }
trap 'perl -e "alarm 30; exec @ARGV" xcrun simctl shutdown "$udid" 2>/dev/null' EXIT
# Boot and wait in one call. A cold boot on a busy Mac can take more than 60 s, and a boot call
# that is stopped early cancels the boot. The driver allows 3 min.
limit 180 xcrun simctl bootstatus "$udid" -b >/dev/null || { echo "Simulator did not boot in 3 min"; exit 1; }
sim privacy "$udid" grant microphone "$BUNDLE" 2>/dev/null
sim status_bar "$udid" override --time 9:41 --batteryState charged --batteryLevel 100

failed=0
run() {
  local name=$1 appearance=$2 seconds=$3
  shift 3
  sim ui "$udid" appearance "$appearance"
  limit "$seconds" xcodebuild test-without-building "${project[@]}" -destination "id=$udid" -resultBundlePath "$OUT/$name.xcresult" \
    -test-timeouts-enabled YES -maximum-test-execution-time-allowance 60 "$@" > "$OUT/$name.log" 2>&1
  local status=$?
  grep -E "Test Case .*(passed|failed)|error:|Executed" "$OUT/$name.log"
  [ "$status" -eq 0 ] || { echo "$name run ended with status $status"; failed=1; }
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
