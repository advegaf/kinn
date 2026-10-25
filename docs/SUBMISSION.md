# Submission

## Written description

Kinn helps a grandparent and a grandchild who do not share a language
talk to each other. Kids of immigrants often lose the language spoken at home,
and the grandparents who hold the family stories cannot tell them.

We built two objects. The Hearth is a framed tablet for the grandmother's
kitchen. It has no buttons: she taps the screen and tells a story in Spanish.
The Almanac is an iPhone app for her grandson, who hears that story in
English, in his grandmother's own voice, while it plays as a short film whose
scenes change as she speaks. The grandson can play the original Spanish,
then record a reply that his grandmother hears in Spanish, in the
grandson's voice.

AI handles each step between them. ElevenLabs Scribe turns speech into text. OpenAI GPT-6
Luna, run through the Codex CLI on a ChatGPT subscription,
translates it while keeping endearments, adds cultural notes, suggests three
questions to ask her, and splits each story into five scenes with film prompts.
ElevenLabs voice clones, made only from samples each person records, speak the
translation. Luma ray-3.2 generates the five scenes, and Supabase carries the
messages between the two devices in real time. The original audio is always
one tap away, so the translation never replaces her.

## Video outline (2 to 3 minutes)

Problem, 30 s. Margaret in Monterrey, Angel in Austin. Angel knows "te quiero" and
little else. The stories are in Margaret's head and in Spanish, and a translation
app is not where anyone tells a story about their mother.

Demo, 90 s. The Hearth on the shelf showing the date. Margaret taps, "te escucho"
and the REC counter, she tells the tamales story. Cut to the iPhone: the week
calendar with the oxblood ribbon on today, the story opens, the dawn kitchen
fades in and the scenes change with her voice in English while the spoken
sentence is highlighted. Tap Hear her original for a few seconds of Spanish.
Write back, pick "What song did your mother sing while you worked?", hold to
record. Back on the Hearth: "Angel te escribió", Margaret taps and hears the
question in Spanish in Angel's voice.

How AI is used, 30 s. Speech to text, a translation that keeps "mijo" and adds
cultural notes, three questions to ask her, five scenes generated from her
words, and each person's own cloned voice in the other language. Mention
consent: voices only from samples they recorded, used only in their thread.

Tools and models, 30 s. ElevenLabs Scribe and Instant Voice Clone with
eleven_multilingual_v2, OpenAI GPT-6 Luna through the Codex CLI on a ChatGPT
subscription (a small relay on our PC), Luma ray-3.2 through
the Agents API, Supabase Postgres, storage, realtime and edge functions, a
SwiftUI iPhone app, a web app in our Android kiosk on an Alexa Tablet 8, and the
printed case. Built with Claude Code as coordinator and parallel subagents.

## Checklist

- [ ] Video is 2 to 3 minutes and uploaded with a public link
- [ ] Public repo link: https://github.com/advegaf/mother-tongue
- [ ] Written description pasted into the form
- [ ] Everyone filmed has signed [CONSENT.md](CONSENT.md)
- [ ] No keys in the repo: confirm `.gitignore` covers `backend/.env`, `story-worker/.env`, `hearth-web/config.local.js` and `ios/Config/Secrets.xcconfig`, check `hearth-web/config.js` and `fire-kiosk/local.properties`, and run a secret scan of the history
