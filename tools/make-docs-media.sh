#!/usr/bin/env bash
# Regenerates the README media kit in docs/images/.
#
#   tools/make-docs-media.sh            build everything, reusing cached captures and renders
#   FRESH=1 tools/make-docs-media.sh    wipe the cache first (new screenshots, new renders)
#   IOS_BUILD=1 ...                     also build and install the iOS app before the simulator shots
#   WORKER_PY=/path/to/python ...       python with story-worker/requirements.txt installed (needed for
#                                       main.py --look; plain system python3 fails)
#   MEDIA_CACHE=/path ...               cache directory (default $TMPDIR/mothertongue-docs-media)
#
# Needs: ffmpeg, ImageMagick (magick), Blender, Google Chrome, Xcode with a booted iPhone 17 Pro
# simulator (SIM_UDID), python3. Pillow and numpy go in a private venv inside the cache.
# Safe to rerun: every step overwrites its output, captures are cached in $CACHE.
#
# Sources, by output:
#   logo.png                 tools/media-src/icon-sunset.png (the chosen app icon, sunset fields),
#                            masked to an iOS rounded square (22.37% radius), 512 px, transparent corners
#   hero.jpg                 hardware/render/showcase-breakfast.png (hearth_showcase.py breakfast)
#   showcase-*.jpg           hardware/render/showcase-{playing,phone,studio}.png
#   hearth-exploded.jpg      hardware/render/hearth-v5-exploded.png
#   case-vs-dream-recorder.jpg  hardware/render/hearth-v4-vs-dr.png
#   hearth-story.gif         hearth-web ?demo=1&state=playing&at=0..1 (36 headless Chrome shots of story 1),
#                            pasted into a Hearth front render (hearth_scene_v4.py front) and crossfaded
#   hearth-states.gif        hearth-web ?demo=1&state=clock|waiting|recording|playing in the same frame
#   ikea-template.png        hearth-web ?template=1 (the SANNAHED mat guide)
#   iphone-entry.gif         iOS app, -openEntry YES -seekFraction 0..1 (30 simulator shots), in a drawn iPhone
#   iphone-{week,write,first}.png  iOS app: week view, -writingBack YES, -onboarded NO
#   luma-scenes.gif          story-worker/luma-check: raw.mp4 re-run through the current worker look
#                            (main.py --look), then scene-2..5.mp4 as they are (no raw kept for those)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/docs/images"
CACHE="${MEDIA_CACHE:-${TMPDIR:-/tmp}/mothertongue-docs-media}"
WORKER_PY="${WORKER_PY:-python3}"   # a python with the story-worker requirements, for --look
RENDER="$ROOT/hardware/render"
LUMA="$ROOT/story-worker/luma-check"
PAPER="EEE8DE"                      # the app's paper colour, behind the iPhone GIF

[ "${FRESH:-0}" = 1 ] && rm -rf "$CACHE"
mkdir -p "$OUT" "$CACHE"

if [ ! -x "$CACHE/venv/bin/python" ]; then
  python3 -m venv "$CACHE/venv"
  "$CACHE/venv/bin/pip" -q install pillow numpy
fi
PY="$CACHE/venv/bin/python"
DM="$ROOT/tools/docs_media.py"

# ffmpeg frames -> GIF: one palette for the whole clip, ordered dither (stable frame to frame, so it
# compresses), only changed rectangles stored.
gif() {  # gif <fps> <frame pattern> <out> [scale]
  ffmpeg -v error -y -framerate "$1" -i "$2" \
    -vf "scale=${4:-960}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=256:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" \
    -loop 0 "$3"
}
jpg() { magick "$1" -background white -alpha remove -alpha off -resize "1920x>" -strip -quality 85 -sampling-factor 4:2:0 "$2"; }

echo "== logo and stills"
"$PY" "$DM" logo "$ROOT/tools/media-src/icon-sunset.png" "$OUT/logo.png"
jpg "$RENDER/showcase-breakfast.png" "$OUT/hero.jpg"
for s in playing phone studio; do jpg "$RENDER/showcase-$s.png" "$OUT/showcase-$s.jpg"; done
jpg "$RENDER/hearth-v5-exploded.png" "$OUT/hearth-exploded.jpg"
jpg "$RENDER/hearth-v4-vs-dr.png" "$OUT/case-vs-dream-recorder.jpg"

echo "== hearth-web captures"
python3 "$ROOT/tools/capture_web.py" "$CACHE/web"
magick "$CACHE/web/template.png" -strip "$OUT/ikea-template.png"

echo "== Hearth frame renders"
# Same camera twice: a black screen (the frame) and a green calibration screen with magenta markers
# (gives the window mask and the texture to render pixel mapping). See docs_media.py hearth.
if [ ! -f "$CACHE/frame-black.png" ] || [ ! -f "$CACHE/frame-calib.png" ]; then
  magick -size 1280x800 xc:black "$CACHE/black.png"
  "$PY" "$DM" calib "$CACHE/calib.png"
  (cd "$RENDER" && HEARTH_SCREEN="$CACHE/black.png" blender -b -P hearth_scene_v4.py -- front "$CACHE/frame-black.png" 96 >/dev/null)
  (cd "$RENDER" && HEARTH_SCREEN="$CACHE/calib.png" blender -b -P hearth_scene_v4.py -- front "$CACHE/frame-calib.png" 32 >/dev/null)
fi

echo "== hearth-story.gif"
rm -rf "$CACHE/story" "$CACHE/story-x"
"$PY" "$DM" hearth "$CACHE/frame-black.png" "$CACHE/frame-calib.png" "$CACHE/story" "$CACHE"/web/story/*.png
"$PY" "$DM" crossfade "$CACHE/story" "$CACHE/story-x" 3 6      # 111 frames at 12 fps, about 9 s
gif 12 "$CACHE/story-x/%04d.png" "$OUT/hearth-story.gif"

echo "== hearth-states.gif"
rm -rf "$CACHE/states" "$CACHE/states-x"
"$PY" "$DM" hearth "$CACHE/frame-black.png" "$CACHE/frame-calib.png" "$CACHE/states" \
  "$CACHE"/web/state-{clock,waiting,recording,playing}.png
"$PY" "$DM" hold "$CACHE/states-x" 28 5 "$CACHE"/states/0{0,1,2,3}.png   # 2.3 s hold + 0.4 s fade each
gif 12 "$CACHE/states-x/%04d.png" "$OUT/hearth-states.gif"

echo "== iOS simulator captures"
python3 "$ROOT/tools/capture_ios.py" "$CACHE/ios" ${IOS_BUILD:+--build}
rm -rf "$CACHE/phone" "$CACHE/phone-entry" "$CACHE/phone-entry-x"
"$PY" "$DM" phone "$CACHE/phone" 1200 none "$CACHE"/ios/{week,write,first}.png
cp "$CACHE/phone/00.png" "$OUT/iphone-week.png"
cp "$CACHE/phone/01.png" "$OUT/iphone-write.png"
cp "$CACHE/phone/02.png" "$OUT/iphone-first.png"

echo "== iphone-entry.gif"
"$PY" "$DM" phone "$CACHE/phone-entry" 640 "$PAPER" "$CACHE"/ios/entry/*.png
"$PY" "$DM" crossfade "$CACHE/phone-entry" "$CACHE/phone-entry-x" 3 6
gif 12 "$CACHE/phone-entry-x/%04d.png" "$OUT/iphone-entry.gif" iw

echo "== luma-scenes.gif"
# Scene 1 through the current (softer) look. The worker writes <name>.look.mp4 beside its input.
if [ ! -f "$CACHE/luma/scene-1.look.mp4" ]; then
  mkdir -p "$CACHE/luma"
  cp "$LUMA/raw.mp4" "$CACHE/luma/scene-1.mp4"
  (cd "$ROOT" && "$WORKER_PY" story-worker/main.py --look "$CACHE/luma/scene-1.mp4")
fi
# 2.2 s from each clip, 0.4 s crossfades, 8 fps, 21:9 at 960 px. The look's grain changes every pixel
# every frame, which GIF cannot compress, so a light blur and a strong temporal denoise hold it under 6 MB.
T=2.2; X=0.4; FPS=8; PRE="gblur=sigma=1.2,hqdn3d=0:0:255:255"
chain=""
for i in 0 1 2 3 4; do chain+="[$i:v]fps=$FPS,scale=960:412:flags=lanczos,$PRE,setsar=1,format=rgb24[v$i];"; done
ffmpeg -v error -y \
  -ss 1 -t $T -i "$CACHE/luma/scene-1.look.mp4" \
  -ss 3 -t $T -i "$LUMA/scene-2.mp4" -ss 3 -t $T -i "$LUMA/scene-3.mp4" \
  -ss 3 -t $T -i "$LUMA/scene-4.mp4" -ss 3 -t $T -i "$LUMA/scene-5.mp4" \
  -filter_complex "${chain}[v0][v1]xfade=duration=$X:offset=1.8[a1];[a1][v2]xfade=duration=$X:offset=3.6[a2];[a2][v3]xfade=duration=$X:offset=5.4[a3];[a3][v4]xfade=duration=$X:offset=7.2,split[a][b];[a]palettegen=max_colors=256:stats_mode=full[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
  -loop 0 "$OUT/luma-scenes.gif"

echo "== sizes"
for f in "$OUT"/*.{png,jpg,gif}; do
  [ -f "$f" ] || continue
  b=$(stat -f %z "$f" 2>/dev/null || stat -c %s "$f")
  flag=""; case "$f" in *.gif) [ "$b" -gt 6000000 ] && flag="  OVER 6 MB";; esac
  printf "%8d KB  %s%s\n" $((b / 1024)) "$(basename "$f")" "$flag"
done
