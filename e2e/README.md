# End to end tests

These are the only tests in this repo (AGENTS.md). They drive the real Hearth and the real
Almanac in demo mode. They need no API keys.

## Hearth

```
python3 e2e/hearth.py
```

Needs Python 3 and agent-browser (`npm i -g agent-browser && agent-browser install`).
It serves hearth-web on a local port and opens it headless at 1340x800 with `?demo=1`.
It presses the button with real key and pointer events and checks each state: clock, waiting,
playing, recording, sending, saved, and error. It checks the new message banner and that a tap
on it plays the message, and the English subtitles (`?subs=en`). It checks that recording
needs a 3 s hold on the button (the ring fills, a shorter tap does not record), and that a
recording that is too short is not sent. On each screen it checks that the right layer shows,
that its text is there, that no text runs off the screen or clips, and that the button zone is
at least 44 px. About 40 s.

## Almanac

```
e2e/ios.sh
```

Run it on a Mac with Xcode. It builds the app and the MotherTongueUITests target, then runs the
UI tests on its own simulator, "Kinn e2e". It covers onboarding, the week, opening a story,
playback, hear her original, write back and send, settings, and going back from each screen.
On each screen it checks touch targets of at least 44 pt, controls clear of the status bar and
the home indicator, and text that runs off the screen. It runs the screens again at the largest
accessibility text size, and runs the color scheme test with the simulator in dark mode.

To run it from Linux, copy the repo to the Mac and run it there:

```
rsync -az --exclude .git --exclude ios/build --exclude e2e/out ./ nethum-mac@100.89.48.117:kinn-review/e2e/
ssh nethum-mac@100.89.48.117 'export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"; cd kinn-review/e2e && e2e/ios.sh'
```

## Results

Each run writes screenshots to `e2e/out/hearth/` and `e2e/out/ios/<run>/` (gitignored).
A failed Hearth check also saves `fail-<scenario>.png`. The exit code is 1 when a test fails.

## Writing tests

Find elements by accessibility identifier (`tabBar.settings`, `entry.back`) or by Hearth
state (`window.hearth.state`), not by layout or copy. When you move or restyle a control,
keep its identifier.
