# Demo video script (target 2:45)

Order follows Meta's suggested breakdown. Film the Hearth in a real kitchen with the real grandmother. Film the grandkid somewhere clearly far away (dorm, campus). Two real phones on screen, no mocked screens.

## 0:00 to 0:30 Problem and hook

Cold open, no title card. Grandma at her kitchen table, speaking Spanish to the camera about something specific (how she met grandpa, the town she grew up in). Subtitles on.

Cut to the grandkid: "I love my abuela. I can't really talk to her. My Spanish stopped at 'te quiero'."

Voiceover: "One in four kids of immigrants can't hold a conversation in their grandparents' language. The people with the most stories end up with nobody who can hear them." (UNVERIFIED statistic. Find a source before using it, or drop the line.)

Title: **Kinn.** Talk to the people you love in the language they love.

## 0:30 to 2:00 Live demo

1. Grandma taps the Hearth's screen and tells a short story in Spanish. The screen shows a gentle "listening" state.
2. The grandkid's phone buzzes. The voice note plays in English, **in grandma's own voice**. Show the "translated voice" badge and tap to hear the original Spanish.
3. Show a cultural note chip ("mija: an endearment, like 'my dear daughter'") and the "Ask her about..." chips.
4. The grandkid taps "Ask her about the bakery in Monterrey" and records a reply in English, in their own words.
5. Back in the kitchen, the Hearth glows. Grandma taps the screen and hears her grandkid's voice speaking Spanish. Hold on her reaction. Don't cut early.
6. Her story comes back as 5 Luma scenes that develop with her voice: the Hearth replays it and each scene changes as she reaches that part of the story. A keepsake of grandma's stories.

## 2:00 to 2:30 How AI is the product

Simple diagram on screen: voice note, then transcription, then a translation that keeps warmth and idioms, then the sender's cloned voice in the target language. In parallel, the AI suggests what to ask next from everything grandma has shared.

Line: "Take the AI out and these two people can't talk. That's how central it is."

Consent line: "Voices are cloned only from a sample each person records themselves, used only in their own family thread, and every translated clip is labeled."

## 2:30 to 2:50 Tools and build

Name the stack plainly: ElevenLabs Scribe for speech to text, OpenAI GPT-6 Luna through the Codex CLI on a ChatGPT subscription for translation, notes, questions and the five scenes, an ElevenLabs voice clone for the translated voice, Luma `ray-3.2` for the story scenes, Supabase realtime and edge functions, SwiftUI on iPhone and iPad, the Hearth web app on Netlify. Mention Claude Code as the build harness and how it helped (parallel agents for backend and iOS, contract-first).

Close on Meta fit: "Portal proved families want a simple device for grandparents. WhatsApp already carries billions of voice notes a day. Kinn is one tap on a voice note: hear it in your language."

## Shot list

- [ ] Signed consent from everyone on camera (docs/CONSENT.md)
- [ ] Grandma voice enrollment sample, 30 s, quiet room
- [ ] Wide shot of the Hearth in the kitchen, plus a close-up of her tap on the screen
- [ ] Grandkid phone screen recording (iOS screen recording plus a camera over the shoulder)
- [ ] The reaction shot. Plan for 3 takes.
- [ ] Diagram slide
