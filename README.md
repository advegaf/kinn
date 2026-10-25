<p align="center">
  <img src="docs/images/logo.png" width="120" alt="Kinn">
</p>

<h1 align="center">Kinn</h1>

<p align="center">
  Grandma tells a story in Spanish. Her granddaughter hears it in English, in her grandma's own voice, and watches it come alive.
</p>

<p align="center">
  <img src="docs/images/hero.jpg" width="960" alt="The Hearth on a breakfast table in morning light, showing Sofía te escribió, with conchas, coffee, daisies and an iPhone open to the Almanac">
</p>

<p align="center">
  <a href="https://mothertongue-hearth.netlify.app/?demo=1">Try the Hearth demo</a>
  <!-- demo video link -->
  · Demo video: coming soon
</p>

<p align="center">
  <sub>Built in 24 hours at HackTX 2026 for the Meta track, Bringing people closer together with AI.</sub>
</p>

> **TL;DR**\
> A framed screen for a grandparent's kitchen and an iPhone app for the grandchild.\
> For families where the grandparents speak one language and the grandkids another.\
> AI translates what each of them says, speaks it in the speaker's own voice, and turns her stories into short films.\
> You can [try the Hearth in your browser](https://mothertongue-hearth.netlify.app/?demo=1) now, no account needed.

Rosa lives in Monterrey. Her granddaughter Sofía lives in Austin, and the
Spanish Sofía has is mostly "te quiero". They love each other and they cannot
really talk.

One morning Rosa sits at her kitchen table and taps the frame on the shelf.
There is nothing to press and nothing to set up. She tells the story of
Christmas when she was a girl: her mother waking her and her sister Lupe at
five, the kitchen dark and smelling of firewood, the yellow bulb over the
table, "ándale, que la masa no espera". The two girls sat on the floor with
the husks in their laps, still damp and warm, and spread the masa thin with
the back of a spoon. Her mother sang very low so their father would keep
sleeping. "Y ya no hay nadie a quien despertar, mija."

An hour later Sofía opens her phone in Austin. She hears the story in English,
in her grandmother's own voice, while the kitchen at dawn fades in scene by
scene. She listens twice. Then she holds the button and asks: will you teach
me this Christmas, at five in the morning? What song was she singing? In
Monterrey the frame says "Sofía te escribió", and Rosa hears the question in
Spanish, in Sofía's voice.

Kids of immigrants often lose the language their family speaks at home. School
is in English and the parents are working, so by the time the kids are old
enough to want the family history, the words for it are gone.

The grandparents are the ones who hold the stories, and those stories go when
they do. Translation apps exist, but nobody tells a story about their mother
into a translation app. Kinn is two objects, one for each side. Rosa
gets the Hearth, a framed screen that does one thing. Sofía gets the Almanac,
an app on her iPhone. Everything said between them crosses the language gap in
the speaker's own voice.

## The Hearth

<p align="center">
  <img src="docs/images/hearth-story.gif" width="760" alt="A story playing on the Hearth as a film, the scene changing as the voice narrates and the Spanish line shown under it">
</p>

The Hearth is an Alexa Tablet 8 (2026) running our web app inside our own
Android kiosk app. It has no buttons. Rosa taps the screen to talk, and taps
again when she is done.

<p align="center">
  <img src="docs/images/hearth-states.gif" width="760" alt="The Hearth moving through its states: the date as a big serif numeral, Sofía te escribió when a reply waits, and te escucho with a REC counter while recording">
</p>

Most of the day it shows the date in a big serif numeral. When her
granddaughter has written back it says "Sofía te escribió". While she talks it
says "te escucho" with a REC counter. Her stories play back as films whose
scenes change with her voice, with the Spanish line on screen.

<p align="center">
  <img src="docs/images/hearth-exploded.jpg" width="760" alt="An exploded render of the printed case: the front bezel, the tablet and the back shell pulled apart">
</p>

It lives in one of two frames. The simple one is an IKEA SANNAHED 25x25 shadow
box with a cream mat cut to a strip window. The other is a 3D printed case
drawn in the language of Modem's Dream Recorder: a front bezel and a back
shell, about 3.7 hours of printing.

<p align="center">
  <img src="docs/images/case-vs-dream-recorder.jpg" width="760" alt="The printed Hearth case beside Modem's Dream Recorder, showing the shared shape and proportions">
</p>

<p align="center">
  <img src="docs/images/ikea-template.png" width="560" alt="The cutting template for the SANNAHED mat, with the strip window marked to the tablet's screen">
</p>

## The Almanac

<p align="center">
  <img src="docs/images/iphone-entry.gif" width="360" alt="The Almanac opening on the iPhone and a story starting to play">
</p>

The Almanac is a SwiftUI app. It shows the week as a calendar, with an oxblood
ribbon on today. Each story opens as a film in five scenes that change as her
voice narrates, and the sentence being spoken is highlighted.

<p align="center">
  <img src="docs/images/iphone-week.png" width="300" alt="The week view of the Almanac, a calendar with an oxblood ribbon marking today">
  <img src="docs/images/iphone-first.png" width="300" alt="A story open in the Almanac, the scene on top and the English text below with the current sentence highlighted">
</p>

Hear her original plays her real voice, in Spanish, so the translation never
replaces her. Write back offers three questions to ask her, drawn from what she
just said. Hold to record. She hears the reply in Spanish, in her
granddaughter's own voice.

<p align="center">
  <img src="docs/images/iphone-write.png" width="300" alt="The Write back screen with three suggested questions and a hold to record button">
</p>

<p align="center">
  <img src="docs/images/luma-scenes.gif" width="760" alt="The five generated scenes of one story cycling in order, each a short film clip with grain">
</p>

## How the AI fits together

| Step | Model | Where it runs |
| --- | --- | --- |
| Speech to text | ElevenLabs Scribe | Supabase edge function |
| Translation that keeps endearments, cultural notes, "ask her about" questions, and the story split into five beats with cinematic prompts | OpenAI GPT-6 Luna through the Codex CLI on a ChatGPT subscription (codex-relay) | Edge function and story worker |
| Voice, so each person is heard in their own voice in the other language | ElevenLabs Instant Voice Clone with eleven_multilingual_v2 | Edge function |
| Scenes, five clips per story | Luma ray-3.2 through the Luma Agents API | Story worker (Python, with an ffmpeg film grain chain adapted from Dream Recorder) |
| Data and realtime | Supabase Postgres, storage, realtime | Supabase |

The full flow is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and the
shared data contract is [docs/CONTRACT.md](docs/CONTRACT.md).

## Privacy and consent

A voice is cloned only from a sample that person records themselves, and it is
used only inside their own family thread. The original audio is always one tap
away. Everyone filmed for the demo signed [docs/CONSENT.md](docs/CONSENT.md).

## Run it yourself

Each part has its own README with the detail. This is the short version.

The backend, on a hosted Supabase project:

```sh
cd backend
supabase link --project-ref <project-ref>
supabase db push
supabase secrets set --env-file .env.secrets   # see backend/README.md
supabase functions deploy process-message enroll-voice make-story --no-verify-jwt
scripts/smoke.sh clip.m4a
```

The Hearth web app:

```sh
cd hearth-web
cp config.example.js config.local.js
python3 -m http.server 8000
open "http://localhost:8000/?demo=1"
netlify deploy --prod --dir . --site mothertongue-hearth
```

The story worker:

```sh
cd story-worker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py --luma-check
caffeinate -i python main.py
```

The iPhone app. Demo mode needs no backend.

```sh
brew install xcodegen
cd ios
cp Config/Secrets.example.xcconfig Config/Secrets.xcconfig
xcodegen generate
open MotherTongue.xcodeproj
```

The tablet:

```sh
cd fire-kiosk
./gradlew assembleDebug -PhearthUrl=https://mothertongue-hearth.netlify.app
scripts/setup-device.sh https://mothertongue-hearth.netlify.app
```

See [backend/README.md](backend/README.md),
[hearth-web/README.md](hearth-web/README.md),
[story-worker/README.md](story-worker/README.md) and
[fire-kiosk/README.md](fire-kiosk/README.md). The case files are
`hardware/cad/stl/front_bezel.stl` and `hardware/cad/stl/back_shell.stl`.

<p align="center">
  <img src="docs/images/showcase-playing.jpg" width="960" alt="The Hearth on a shelf playing a story, a warm scene on screen inside the cream frame">
</p>

<p align="center">
  <img src="docs/images/showcase-phone.jpg" width="470" alt="A hand holding the iPhone with the Almanac open on a story">
  <img src="docs/images/showcase-studio.jpg" width="470" alt="The printed case and the tablet on a work table during the build">
</p>

## How we built it

We built this with Claude Code working as a coordinator with parallel subagents.
We wrote a shared contract first ([docs/CONTRACT.md](docs/CONTRACT.md)) so the
backend, the Hearth, the iPhone app and the worker could be built at the same
time against the same tables. We checked every screen by screenshot before
accepting it. We explored the design as four variants and refined one
(`design/iterations/`), and modeled the case as signed distance fields and
rendered it in Blender. We approved every plan and read the changes.

## Credit

Built by [Angel Vega](https://github.com/advegaf) and
[Nethum](https://github.com/nethum529).

The look, the case language and the ffmpeg chain come from Modem's
[Dream Recorder](https://github.com/modem-works/dream-recorder), which is MIT.
The demo scene photos are from Lorem Picsum, under the Unsplash licence.
Instrument Serif and Inter are under the SIL Open Font License.

## Licence

MIT. See [LICENSE](LICENSE).
