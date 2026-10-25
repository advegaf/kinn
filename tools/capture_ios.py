"""Simulator screenshots of the iOS app for the docs media kit.

Usage: python3 tools/capture_ios.py <outdir> [--build]
Needs a booted simulator (UDID below, override with SIM_UDID). With --build it first builds the app
into ios/build/DD-media and installs it. Every shot terminates the app, waits 2 s, launches it in
demo mode as Angel (family, English) with extra launch arguments, waits 9 s, then screenshots:
  week.png         the Almanac week view (no extra args)
  write.png        -writingBack YES
  first.png        -onboarded NO (first screen of onboarding)
  entry/NN.png     -openEntry YES -seekFraction NN/29, 30 frames of one entry's story
Existing files are skipped. Delete the outdir to force a fresh capture.
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UDID = os.environ.get("SIM_UDID", "A9EFBF02-6A11-46D6-A702-43AE720AE49B")
BUNDLE = "com.hacktx.mothertongue"
APP = os.path.join(ROOT, "ios/build/DD-media/Build/Products/Debug-iphonesimulator/MotherTongue.app")
BASE = ["-demoMode", "YES", "-onboarded", "YES", "-role", "family", "-name", "Angel", "-lang", "en"]
ENTRY_FRAMES = 30


def run(*cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def shot(out, extra):
    if os.path.exists(out):
        return
    args = list(BASE)
    for i in range(0, len(extra), 2):  # later values win, so drop BASE duplicates
        if extra[i] in args:
            j = args.index(extra[i])
            del args[j:j + 2]
    subprocess.run(["xcrun", "simctl", "terminate", UDID, BUNDLE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    run("xcrun", "simctl", "launch", UDID, BUNDLE, *args, *extra)
    time.sleep(9)
    run("xcrun", "simctl", "io", UDID, "screenshot", out)
    print("ios:", os.path.basename(out))


def main():
    outdir = os.path.abspath(sys.argv[1])
    if "--build" in sys.argv:
        run("xcodebuild", "-project", os.path.join(ROOT, "ios/MotherTongue.xcodeproj"), "-scheme", "MotherTongue",
            "-destination", f"id={UDID}", "-derivedDataPath", os.path.join(ROOT, "ios/build/DD-media"), "build")
        run("xcrun", "simctl", "install", UDID, APP)
    os.makedirs(os.path.join(outdir, "entry"), exist_ok=True)
    run("xcrun", "simctl", "status_bar", UDID, "override", "--time", "9:41", "--batteryState", "charged",
        "--batteryLevel", "100", "--cellularBars", "4", "--wifiBars", "3")
    shot(os.path.join(outdir, "week.png"), [])
    shot(os.path.join(outdir, "write.png"), ["-writingBack", "YES"])
    shot(os.path.join(outdir, "first.png"), ["-onboarded", "NO"])
    for i in range(ENTRY_FRAMES):
        f = i / (ENTRY_FRAMES - 1)
        shot(os.path.join(outdir, "entry", f"{i:02d}.png"), ["-openEntry", "YES", "-seekFraction", f"{f:.3f}"])
    subprocess.run(["xcrun", "simctl", "terminate", UDID, BUNDLE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
