# Hearth Fire kiosk

Tiny Android app that turns an Alexa Tablet 8 (2026) into the Hearth display. A Fire HD 8 works too. It is one full screen WebView pointed at the hearth-web URL. It acts as the home app, comes back after reboot, keeps the screen on, and grants the WebView mic access.

No androidx. minSdk 28 (Fire OS 7+ or Android 9+), target 34. Main target: Alexa Tablet 8 (2026, Android 16 with Google Play). The Fire HD 8 also runs it.

## Setup on the Mac

Paste into every shell:

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$PATH"
```

First time on a new Mac: `brew install openjdk@17 android-commandlinetools`, then `sdkmanager --licenses`. Gradle downloads the rest.

## Build

```sh
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

Without `-PhearthUrl` the baked in default is `https://example.invalid`, so pass the real URL at setup or bake it in:

```sh
./gradlew assembleDebug -PhearthUrl=https://mothertongue-hearth.netlify.app/
```

## Put it on the tablet

Enable USB debugging first (steps are at the top of `scripts/setup-device.sh`; they are written for Fire OS, and the Alexa Tablet 8 menus may be named differently), plug in, then:

```sh
scripts/setup-device.sh "https://mothertongue-hearth.netlify.app/?thread=<uuid>&profile=<uuid>"
```

Usage is `scripts/setup-device.sh <url> [apk]`. The script installs the APK, grants the mic, sets Hearth as the home app, keeps the screen on while plugged in, and launches with the URL.

Change the URL later without reinstalling (the app saves it):

```sh
adb shell am start -S -n com.hacktx.mothertongue.hearth/.MainActivity --es url "'https://new.url/'"
```

URL priority: `--es url` extra, then the saved URL, then the `-PhearthUrl` build default.

## Local test

```sh
scripts/setup-device.sh "http://<mac-lan-ip>:8765/?demo=1"
```

The mic only works on https (or localhost). An http LAN URL checks load, full screen, keys and autoplay, not the mic. For the mic, use an https tunnel or the deployed URL.

## Undo

```sh
adb uninstall com.hacktx.mothertongue.hearth
adb shell settings put global stay_on_while_plugged_in 0
```
