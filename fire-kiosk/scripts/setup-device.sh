#!/usr/bin/env bash
# Turn a USB connected Fire tablet into the Hearth kiosk.
#
# Usage: scripts/setup-device.sh <hearth-url> [apk-path]
#   e.g. scripts/setup-device.sh https://hearth.example.com/
#
# Before running, on the Fire:
#   1. Settings > Device Options > About Fire Tablet: tap "Serial Number" 7 times.
#      Developer Options now shows under Device Options.
#   2. Device Options > Developer Options: turn on "USB debugging" (and "ADB" on older Fire OS).
#   3. Plug into the Mac, unlock, and accept the "Allow USB debugging?" prompt (tick "Always allow").
#   4. Set the lock screen to none: Settings > Security & Privacy > Lock Screen Passcode > off.
#      A PIN or swipe lock still shows after reboot and the kiosk sits behind it.
#      The Fire OS lock screen (with its ads on Special Offers models) cannot be removed by adb.
#
# Microphone: Chrome WebView only allows getUserMedia on https (or localhost).
# A plain http LAN URL proves load, full screen, keys and autoplay, but the mic stays off.

set -euo pipefail

PKG=com.hacktx.mothertongue.hearth
ACT="$PKG/.MainActivity"
URL="${1:-}"
APK="${2:-$(cd "$(dirname "$0")/.." && pwd)/app/build/outputs/apk/debug/app-debug.apk}"

if [ -z "$URL" ]; then
  echo "usage: $0 <hearth-url> [apk-path]" >&2
  exit 1
fi

command -v adb >/dev/null || { echo "adb not on PATH (see README env exports)" >&2; exit 1; }
[ -f "$APK" ] || { echo "APK not found: $APK (run ./gradlew assembleDebug)" >&2; exit 1; }

count=$(adb devices | awk 'NR>1 && $2=="device"' | wc -l | tr -d ' ')
if [ "$count" -eq 0 ]; then
  echo "no authorized device. adb devices says:" >&2
  adb devices >&2
  echo "check the cable, USB debugging, and the allow prompt on the tablet" >&2
  exit 1
fi
if [ "$count" -gt 1 ] && [ -z "${ANDROID_SERIAL:-}" ]; then
  echo "more than one device. set ANDROID_SERIAL to pick one." >&2
  adb devices >&2
  exit 1
fi

echo "device: $(adb shell getprop ro.product.model | tr -d '\r') (Fire OS $(adb shell getprop ro.build.version.name | tr -d '\r'))"

echo "installing $APK"
adb install -r -g "$APK"

echo "granting mic"
adb shell pm grant "$PKG" android.permission.RECORD_AUDIO || true

echo "setting as home app"
adb shell cmd package set-home-activity "$ACT" || echo "set-home-activity failed; press Home once and pick Hearth > Always"

echo "keeping the screen on while plugged in"
adb shell settings put global stay_on_while_plugged_in 3
adb shell settings put system screen_off_timeout 2147483647

echo "launching with url $URL"
# The url extra is saved by the app, so later launches and reboots reuse it.
adb shell am start -S -n "$ACT" --es url "'$URL'"

echo "done"
