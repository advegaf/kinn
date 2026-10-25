# Hearth (web)

Grandma's side of Hearth. A single static page that runs full screen on an Alexa Tablet 8 (2026, 1340 x 800 landscape) inside the fire-kiosk app (`../fire-kiosk/`), behind the printed case (`../hardware/`) or a cream mat in a shadow box frame. Fully Kiosk Browser works as an alternative. There is no physical button. She taps the screen to tell a story, and the strip shows when her grandkid's reply is waiting. Another tap plays it in Spanish, in the grandkid's cloned voice.

Hosted on Netlify: https://mothertongue-hearth.netlify.app (add `?demo=1` for the demo, `?template=1` for the mat template, `?calibrate=1` to fit the strip).

Every state sits on night with grain and a soft vignette, in the v4c "Almanac" design (`../design/DESIGN.md`): Instrument Serif for the day numeral, headlines and captions, Inter for the tape counter and the REC status, lamp white for the optional button light, muted red only for REC. Fonts are bundled in `fonts/` (OFL), with Google Fonts as a fallback. Playing keeps the dark cinematic strip. That strip and the state machine are adapted from [Dream Recorder](https://github.com/modem-works/dream-recorder) by Modem (MIT): the black strip, the vignette and the fades.

Plain HTML, CSS and ES modules. No build step. supabase-js loads from a pinned jsDelivr URL, and only when not in demo mode.

## Story scenes

A story with `story.scenes` (`docs/CONTRACT.md`) develops with the narration. The scene shown is the last one whose start is at or below the playback fraction, and the caption shows that beat's Spanish text.

- Her own story plays her original audio, so scenes are timed by each beat's `text_es` offset in `transcript`. Without those, the worker's `start`/`end`, else even spacing.
- A family reply spreads the related story's scenes evenly over the reply, and the caption is the reply text.
- Progress comes from the audio element's `timeupdate`. Demo speech uses `speechSynthesis` boundary events, and when none arrive for 1.5 s, elapsed time over an estimate (160 words a minute) carries on.
- Stills crossfade over 2 s (the outgoing one out in 1.2 s) with a slow drift. A scene `video_path` plays over its still once it runs.
- Long beats step down from 14 to 11, 9.5 or 8.5 strip units and never pass 3 lines.

## Screen layout

- The visible strip is the mat window. It is a rect in percent of the screen (default full width, 25% to 75% high) saved with the calibration. Sizes inside it are in strip units (1% of strip height, 4px at the default), so a recalibrated strip scales everything.
- Everything outside the strip is behind the case or mat and stays black. All feedback lives in the strip.
- Optional button build only (`BUTTON = True` in `../hardware/cad/hearth_v4_sdf.py`): the button zone is a rect in percent of the screen, and a lamp-white spot under it shows through the button cap (faint when idle, a slow 7 s breathe when a reply waits, dark-dim while recording, sending and playing). In the current button-free build the zone code still runs, but the default zone sits outside the strip, behind the case, where nobody touches it.

## States and taps

| State | A tap on the strip does |
| --- | --- |
| clock (idle) | starts recording. A tap on the "Escuchar otra vez" panel opens past |
| past | plays the story or reply on the card. "Siguiente" shows the next older one, "Volver" goes back. After playback it comes back here, and it leaves on its own after 60 s |
| recording | stops and sends |
| sending | nothing, it waits until the row is `ready` |
| waiting | plays the newest unheard reply |
| playing | stops playback |
| error | goes back to clock (it also returns on its own after 3.5 s) |

A tap anywhere on the visible strip counts (`press('strip')` in `js/main.js`). Enter, Space, Play/Pause and the volume up key count too (`press('key')`), so a Bluetooth shutter remote works. In the optional button build, a touch in the button zone also counts. Taps closer than 250 ms are ignored. In recording, playing and past, a tap less than 650 ms after the state starts is ignored. The panel on the right 25% of the strip shows only when there is at least one ready story or reply. Keys always do the main action of the state.

## Config

```sh
cp config.example.js config.local.js   # gitignored
```

Fill in `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `PROFILE_ID` (grandma's elder profile) and `THREAD_ID`. URL params override the ids: `?thread=<uuid>&profile=<uuid>`.

Other params:

- `?demo=1` canned data, fake mic, no backend. Add `&state=clock|waiting|recording|sending|playing|past|error` to jump to a state.
  Demo data is `demo/demo-stories.json` (6 stories of Margaret's, 5 scenes each, stills in `demo/scenes/`, plus 2 replies from Angel). Demo narration is pre-generated ElevenLabs audio at `demo/audio/{id}-{es|en}.mp3`. Files exist for `s1` to `s3` (both languages) and `r1-en`; anything missing falls back to `speechSynthesis`. With `&state=playing`, `&msg=<id>` picks the row (`s1` to `s6` her stories, `r1` or `r2` a reply).
- `&at=0..1` (DEBUG, with `state=playing`) freezes playback at that fraction of the narration with no sound, for screenshots. Without `&msg` it plays her newest story.
- `?calibrate=1` strip overlay, plus the button zone for the optional button build (below).
- `?template=1` full screen mat cutting guide (below).
- `?debug=1` logs state changes and presses to the console.

The anon key is a public client key and ships to the browser anyway. Keep it out of git; use the Netlify deploy below.

## Run locally

```sh
cd hearth-web
python3 -m http.server 8000
open "http://localhost:8000/?demo=1"
```

The mic needs a secure context. `http://localhost` works on the laptop, but `http://<laptop-ip>:8000` on the tablet will not get the mic. Test on the tablet through the Netlify HTTPS URL (or an ngrok tunnel).

## Deploy (Netlify)

```sh
cd hearth-web
netlify deploy --prod --dir . --site <site>
```

`<site>` is the Netlify site name or id for https://mothertongue-hearth.netlify.app. It is a static site, no framework preset needed. The device reads Supabase settings from `config.local.js`, so deploy from a folder that has it, then confirm it was uploaded with `curl -I https://mothertongue-hearth.netlify.app/config.local.js` (expect 200). If it is missing, the Hearth shows a small "[ falta configurar ]" note in the bottom left of the strip.

## Device setup (Alexa Tablet 8)

Use the fire-kiosk app: one full screen WebView that acts as the home app, keeps the screen on and grants the mic. See `../fire-kiosk/README.md`. In short:

```sh
cd ../fire-kiosk
scripts/setup-device.sh "https://mothertongue-hearth.netlify.app/?thread=<uuid>&profile=<uuid>"
```

Lock the tablet to landscape and turn screen brightness up.

### Alternative: Fully Kiosk Browser

1. Sideload Fully Kiosk Browser. Some of the settings below need Fully PLUS (about $7).
2. Web Content Settings: Start URL `https://mothertongue-hearth.netlify.app/?thread=<uuid>&profile=<uuid>`. Enable Autoplay Videos, Autoplay Audio and Microphone Access. Load the page once and accept the mic prompt.
3. Web Zoom and Scaling: zoom 100%, zooming disabled. The layout is all percentages.
4. Device Management: Keep Screen On, Screen Orientation Landscape.
5. Fullscreen or Kiosk Mode: hide the status and navigation bars. Disable Swipe to Go Back and Pull to Refresh.

If a reply does not play on the first tap after a reboot, autoplay is blocked. The page retries on the next touch release; turning on autoplay in the kiosk is the real fix.

## IKEA SANNAHED mat build (alternative to the printed case)

The tablet sits behind a cream mat board in an IKEA SANNAHED 25x25 shadow box frame.

1. Remove the plastic front from the frame.
2. Open `?template=1` on the tablet. It shows the strip window in white on black, with distances in cm: about 19.0 x 5.7 cm, the full active width and the middle half of the 19.0 x 11.35 cm active area. Hold the mat against the glass and trace it.
3. Cut the strip window. No button hole: she taps the screen through the window. (The template still draws a button hole for the optional button build. Ignore it.)
4. Foam tape the tablet behind the mat, lined up with the cut.
5. Drill a hole in the back panel for the USB-C cable.
6. Run `?calibrate=1` on the device and fit the strip to the real cut.

## Calibrate the strip

1. Open the start URL with `&calibrate=1` added.
2. Drag the strip outline (or its corner handle) until it matches the mat or bezel window. Its size shows in percent and cm.
3. Remove `&calibrate=1` from the start URL. The strip is saved in localStorage on the device (Default strip resets it).

Optional button build only: the overlay also shows the button zone. Press the cap a few times; each touch shows a dot, green inside the zone and red outside, with a hit count. Tap Center on last touch or drag the zone onto where the stylus tip lands. The circle is the button hole. Check 10 presses read 10 / 10 and that no dots appear after 5 minutes idle. Keep the zone above the dashed 94% line, because Android gesture navigation owns the bottom edge. Default button resets the zone.

## Data flow

Follows `docs/CONTRACT.md`:

1. Record with MediaRecorder (`audio/webm;codecs=opus`, falls back to `audio/webm` then `audio/mp4`).
2. Upload to bucket `audio` at `{thread_id}/{message_id}.webm`.
3. Insert the `messages` row (`status 'uploaded'`, `source_lang 'es'`, `target_lang 'en'`), then invoke `process-message`.
4. Realtime subscription on `messages` for the thread, plus a 3 s poll.
5. Unheard means sent by family, `status 'ready'`, `heard_at` null. Playing sets `heard_at` (and remembers it locally in case the update fails).
6. Playback plays `translated_path` from `audio`, with the story video (`story.video_path`) muted and looping. Without a video it uses `story.image_paths` or `thumb_path` with a slow Ken Burns, and without either a warm gradient. A story still `generating` or in `error` counts as no story. Family replies borrow the newest real story in the thread. `story.title_es` shows at the top of the strip.

## Files

- `index.html` markup
- `styles.css` v4c Almanac styles: bundled fonts, strip units, night grain and vignette, lamp light, states, motion
- `fonts/` Instrument Serif and Inter (OFL)
- `config.js` loads `config.local.js` and URL params
- `js/main.js` state machine, input, playback
- `js/backend.js` Supabase client and the demo backend
- `js/recorder.js` mic capture and level meter
- `js/calibrate.js` strip and (optional) button zone storage, the calibration overlay and the mat template
