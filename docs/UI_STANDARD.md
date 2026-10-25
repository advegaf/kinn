# Kinn UI standard

This is the checklist for every screen in the Almanac (iOS) and the Hearth
(hearth-web, and the SwiftUI elder view). A reviewer uses it on each screen.

## How to use this checklist

1. Run the app (Hearth: agent-browser at 1340x800 with ?demo=1. Almanac:
   the iOS simulator in demo mode). Take a screenshot of each state.
2. Go through each section below. Each rule has an ID, one check, and a
   source key. The keys are in "Sources" at the end.
3. Report a failed rule with its ID, the screen, and the proof (a
   screenshot, a measured value, or a file and line).
4. When two rules disagree, use this order: AGENTS.md, then this file,
   then design/DESIGN.md.

Units: pt is iOS points. px is CSS pixels. On the Hearth, u is 1 percent
of the strip height (4 px for the default strip, 1340x400 on a 1340x800
screen).

## 1. Kinn house rules

- [ ] K1. No eyebrow headers. No small label (upper case or letter spaced)
  above or beside a title or a section. [AG]
- [ ] K2. No italic type anywhere. Show the second language with size and
  color, not with italic. [AG]
- [ ] K3. No default Apple look for navigation and bars. Use the Kinn
  paper and serif style on every new surface. [AG] [DS]
- [ ] K4. Two type families only: Instrument Serif and Inter. No SF Pro
  or system fonts in product UI. [DS]
- [ ] K5. One accent color at a time: ribbon on paper, lamp on the Hearth
  button, rec red only for recording. [DS]
- [ ] K6. Capitalize names and labels. Use sentence case for UI text. No
  all caps text. [AG]
- [ ] K7. Fades only for state changes. No bounce, no spring overshoot,
  no sliding, no spinners. [DS] [EK]
- [ ] K8. Show only what the person needs now. Do not crowd a screen. [AG]
  [LUX-HICK]

Note: design/DESIGN.md still asks for italic English subtitles and Inter
tiny caps labels. K1 and K2 replace those parts of DESIGN.md.

## 2. Laws of UX applied to Kinn

- [ ] G1. Fitts: the primary action is large and near the hand. Hearth:
  the whole strip is the target. Almanac: the main action is in the
  bottom half. [LUX-FITTS]
- [ ] G2. Hick: one primary action per screen. Put other actions one step
  away. [LUX-HICK] [JK-LAYOUT]
- [ ] G3. Jakob: use the platform patterns people know. iOS swipe back
  works on every pushed screen. Play and record use the common icons
  or words. [LUX-JAKOB]
- [ ] G4. Miller: chunk content. A week shows 7 days, a story shows one
  beat at a time. [LUX-MILLER]
- [ ] G5. Doherty: show a visible response within 400 ms of each tap.
  [LUX-DOHERTY]
- [ ] G6. Tesler: the system holds the complexity. Neither person sees
  translation, upload, or processing steps, only a calm wait state.
  [LUX-TESLER]
- [ ] G7. Aesthetic-usability: keep the paper and serif look the same on
  every screen. One screen in a different style breaks trust.
  [LUX-AESTH]
- [ ] G8. Peak-end: the end of a story and the moment a reply is sent get
  a clear, warm close (a short line of text, not a toast). [LUX-PEAK]
- [ ] G9. Von Restorff: only the primary action looks different from the
  rest. [LUX-VONR]
- [ ] G10. Serial position: put the newest story first and the main
  action last in reading order. [LUX-SERIAL]
- [ ] G11. Goal-gradient: show progress while a story is processed.
  [LUX-GOAL]
- [ ] G12. Zeigarnik: an unheard reply or an unfinished story shows a
  clear "waiting" state until it is done. [LUX-ZEIG]
- [ ] G13. Proximity and common region: a label sits closer to its
  control than to the next group. The gap between groups is at least 2
  times the gap inside a group. [LUX-PROX] [LUX-REGION] [JK-LAYOUT]
- [ ] G14. Postel: accept short, long, quiet, or noisy recordings, and
  forgive a wrong tap. [LUX-POSTEL]

## 3. Touch and layout

- [ ] L1. Every touch target is at least 44x44 pt on iOS. The visible
  shape can be smaller, the hit area cannot. [HIG-ACC] [AG]
- [ ] L2. On the web, every target is at least 44x44 px (WCAG 2.5.5).
  Android minimum is 48x48 dp. [W-2.5.5] [AND-48]
- [ ] L3. Targets do not touch. Leave at least 8 dp between small
  targets, 12 px between filled controls, and 24 px between borderless
  text controls. [AND-48] [JK-LAYOUT]
- [ ] L4. Primary actions on the phone sit in the bottom half, in easy
  thumb reach. [SM-THUMB]
- [ ] L5. Text and controls stay inside the safe areas. Backgrounds and
  media can bleed to the edges. [HIG-LAY] [JK-LAYOUT]
- [ ] L6. One spacing scale. Use steps of 4 pt (4, 8, 12, 16, 24, 32,
  48). Check each padding and gap against its neighbors. [AG] [JK-LAYOUT]
- [ ] L7. Align to a small set of shared edges. Page margin is the same
  on every screen. [JK-LAYOUT]
- [ ] L8. A control looks like a control: it has a shape, an underline,
  or a fixed place. A control in the same style as a label fails.
  [JK-LAYOUT] [NNG-MOB]
- [ ] L9. Hidden content has a visible cue (a peek of the next item, or
  a disclosure control). [JK-LAYOUT]

## 4. Type

- [ ] T1. Body text is 17 pt or larger on iOS. No text is below 11 pt.
  [HIG-TYP]
- [ ] T2. Text scales with Dynamic Type. Use Font.custom(_:size:relativeTo:)
  or @ScaledMetric, not fixedSize, except for display numerals that have
  a fixed box. Check at the largest accessibility size. [HIG-TYP]
- [ ] T3. On the web, text can resize to 200 percent with no loss, and
  it reflows with no sideways scroll. [W-1.4.4] [W-1.4.10]
- [ ] T4. Line height: display 1.0 to 1.1, headings 1.2 to 1.3, body
  1.4 to 1.6. Text of 3 or more lines uses at least 1.4. [JK-TYPE]
- [ ] T5. Line length is 60 to 75 characters at most for long text.
  [JK-TYPE]
- [ ] T6. Tabular numbers on all numbers that change or align (clock,
  counter, day numerals, codes). [JK-TYPE] [DS]
- [ ] T7. Headings at 24 pt and up use tracking of -0.01 to -0.02 em.
  Body text uses 0. [JK-TYPE]
- [ ] T8. No glyph is clipped. Check descenders and accents (n tilde,
  accented i) at every size. [AG]

## 5. Color and contrast

- [ ] C1. Text contrast is at least 4.5:1. Large text is at least 3:1.
  Large text on the web is 24 px, or 18.7 px bold [W-1.4.3]. Large text
  on iOS is 18 pt and up, or bold at any size [HIG-ACC].
- [ ] C2. Icons, control edges, and focus rings are at least 3:1 against
  their background. [W-1.4.11]
- [ ] C3. Text over a photo or video has a scrim, so C1 holds on the
  brightest frame. Measure on the brightest frame. [W-1.4.3]
- [ ] C4. Color is never the only signal. Recording has the word and
  the dot, not only red. [W-1.4.1]
- [ ] C5. Inactive text (future days) can be lighter, but it still must
  be readable if it carries information. [W-1.4.3]

Measured token contrast (WCAG formula):

| Token pair | Ratio | Result |
| --- | --- | --- |
| ink on paper | 14.27 | pass |
| soft #6F6B65 on paper | 4.34 | iOS: fails under 18 pt, passes at 18 pt and up |
| sub #77726B on paper | 3.91 | iOS: fails under 18 pt, passes at 18 pt and up |
| fog #8E8A84 on paper | 2.82 | fails |
| muted #A39D94 on paper | 2.21 | fails |
| later #BDB7AE on paper | 1.63 | fails |
| fog #8E8A84 on night | 5.74 | pass |
| Hearth idle weekday #6E6A64 on night | 3.66 | large text only |
| Hearth idle month and clock #57544F on night | 2.61 | fails |

## 6. Motion and haptics

- [ ] M1. Respect Reduce Motion. Under it, replace movement, scale, and
  blur with an opacity fade. Repeating glows stop. [HIG-ACC] [HIG-MOT]
  [W-2.3.3] [JK-UI]
- [ ] M2. UI motion stays under 300 ms. Button press feedback is 100 to
  160 ms. Exits are shorter than enters. [EK] [JK-UI]
- [ ] M3. Use ease-out for things that enter or respond. Never ease-in
  for UI. [EK]
- [ ] M4. Nothing appears from scale 0. Start at 0.95 or more, with
  opacity. Press scale is 0.96 to 0.98. [EK] [JK-UI]
- [ ] M5. Motion is never the only feedback. Each animated change also
  changes a word, icon, or color. [JK-UI] [HIG-HAP]
- [ ] M6. Haptics confirm an action (start record, send). They are never
  the only feedback, and they match the visual event. [HIG-HAP]
- [ ] M7. No flashing more than 3 times per second. [W-2.3.1]

## 7. Feedback and states

- [ ] F1. Each screen has a defined loading, empty, error, and success
  state. The reviewer sees each one. [NNG-EMPTY] [NNG-ERR]
- [ ] F2. A wait under 1 s shows no indicator. A wait over 1 s shows a
  calm state with words. A wait over 10 s shows progress or a step.
  [NNG-RT] [HIG-PROG]
- [ ] F3. Content that loads uses a placeholder in the shape of the
  content, not a spinner. [NNG-SKEL] [DS]
- [ ] F4. An empty state says what will appear here and what to do next.
  [NNG-EMPTY]
- [ ] F5. An error says what happened and what to do, in plain words, in
  the reader's language, with no blame and no code. [NNG-ERR] [W-3.3.1]
- [ ] F6. After each action the person sees that it worked (sent,
  saved, playing). [NNG-SEN] [LUX-DOHERTY]

## 8. Navigation and gestures

- [ ] N1. Every gesture has a visible on-screen alternative (a button).
  [HIG-ACC] [HIG-GES] [W-2.5.1]
- [ ] N2. Any drag or press-and-hold has a single tap alternative.
  [W-2.5.7]
- [ ] N3. Swipe back works on every pushed screen. A modal has a visible
  close control. [HIG-GES] [LUX-JAKOB]
- [ ] N4. One gesture has one meaning on a screen. [NNG-MOB]
- [ ] N5. No long press for anything a person needs. [NNG-SEN] [AG]

## 9. Accessibility

- [ ] A1. Each control has a VoiceOver label that says what it does. A
  custom control has the button trait. [HIG-ACC]
- [ ] A2. Decorative views (grain, vignette, rules) are hidden from
  VoiceOver. [HIG-ACC]
- [ ] A3. Web focus is visible and not hidden by other content.
  [W-2.4.7] [W-2.4.11]
- [ ] A4. Story video and audio have captions in the reader's language.
  [W-1.2.2]
- [ ] A5. No time limit, or the person can extend it. A message that
  goes away on its own stays at least long enough to read twice.
  [W-2.2.1]

## 10. Writing in the UI

- [ ] W1. Use the words of the person, not of the system ("Sending to
  Angel", not "Uploading"). [NNG-ERR] [AG]
- [ ] W2. Button labels are verbs ("Write back", "Listen"). [NNG-ERR]
- [ ] W3. Short sentences. One idea per line. [AG]
- [ ] W4. Text names a control that exists. Do not say "press the
  button" on a device with no button. [NNG-SEN]

## 11. The Hearth (older user, kitchen tablet, 1340x800)

Context: Margaret is older and reads Spanish. The Hearth hangs in a kitchen
frame. She sees it from across the room and touches it with one finger,
maybe with wet or floury hands. Only the strip (default 1340x400 in the
middle of the screen) is visible.

- [ ] H1. One action per state, and the screen says it in words: what a
  tap does now ("Toca para contar una historia"). [NNG-SEN] [LUX-HICK]
  [AG]
- [ ] H2. The whole visible strip is the target. No small targets. [LUX-FITTS]
- [ ] H3. No hidden gestures. No double tap, long press, or swipe for any
  action. An extra shortcut is fine only if a visible path also exists.
  [NNG-SEN] [W-2.5.1] [AG]
- [ ] H4. A stray second tap never loses a story. A tap mistake can be
  undone. [NNG-SEN] [LUX-POSTEL]
- [ ] H5. A visible change within 400 ms of each tap. [LUX-DOHERTY]
- [ ] H6. Readable from across the kitchen. The key line reads at 3 m
  (10 ft) [AMZ-MM]. Kinn decision: no text below 8u (32 px), main line
  at least 22u (88 px). Check by eye from 3 m.
- [ ] H7. All text is at least 4.5:1, also the dim idle clock. The idle
  screen can be quiet, but it must be readable. [W-1.4.3] [AMZ-MM]
- [ ] H8. One main element per state. At most 3 elements on the strip.
  [AMZ-MM]
- [ ] H9. Clear feedback after each action: recording shows REC and the
  time, sending shows a calm line, sent shows "sent to Angel". [NNG-SEN]
- [ ] H10. Errors stay on screen until she can read them twice, and say
  what to do next. [W-2.2.1] [NNG-ERR]
- [ ] H11. All words are in her language (Spanish), in sentence case.
  [AG] [WAI-OLD]
- [ ] H12. Captions on every story and reply. Caption text over a bright
  scene has a scrim. [W-1.2.2] [W-1.4.3]
- [ ] H13. Fades only, slow and calm. No flashing, no busy motion.
  [W-2.3.1] [DS]
- [ ] H14. Settings and setup are not reachable by a hidden gesture on
  the elder screen. Setup is done by the family, through a visible path.
  [NNG-SEN] [W-2.5.1]

## 12. Reference apps

| App | What it does well | Idea Kinn takes | Source |
| --- | --- | --- | --- |
| Things 3 | One round "+" button is always there. Today and This Evening split the day into two calm parts. | Each screen has one always visible primary action that works with one tap. | [REF-THINGS] |
| Day One | The entry screen is a bare writing page with few controls. A critique found that nothing shows that an entry can be opened. | Every tappable thing (play, open, record) shows a visible cue before the tap. | [REF-DAYONE] |
| Duolingo | Celebrations are tuned by hand. The team changed a symbol that did not work across cultures. | Test each symbol and each celebration with people of the other language. Prefer pictures that need no words. | [REF-DUO] |
| Headspace | One warm illustration style makes hard topics feel safe. Motion is art directed. | Each empty state and each wait uses the same warm style, never a bare spinner or a blank page. | [REF-HEAD] |
| Airbnb (2023) | One trust mark (Guest favorite) instead of many small badges. | Use one clear mark (for example "new") instead of many small labels. | [REF-AIRBNB] |
| Apple Journal | A suggestion can be saved with no typing. Voice recording is in the compose bar. | Give a reply path with no typing: one tap to record a voice note. Label the main button with words. | [REF-JOURNAL] |
| Amazon Echo Show | Text must read at 3 ft and 10 ft. The main element is the most important information. Each touch action has a voice match. | On the Hearth, one main element per state, readable at 3 m, 4.5:1 contrast. | [AMZ-MM] |

## 13. Current Kinn screens that break a rule

Found on 2026-10-25. Hearth web: run in demo mode at 1340x800 with
agent-browser, a screenshot of each state, and a read of the code. iOS: a
read of the current code, checked against the screenshots in docs/screens
(ios-v4c-week.png for the Almanac, ios-v2-hearth.png for the elder
Hearth). The iOS app builds. New simulator screenshots were not taken,
because the shared simulator on the build Mac hung. Layout, touch bounds,
safe areas, largest Dynamic Type, and Reduce Motion on iOS are not yet
checked on a device.

### Hearth web (hearth-web)

| Screen | Rule | What is wrong | Proof |
| --- | --- | --- | --- |
| Clock (idle) | H1 | No words say what a tap does. She must know that a tap starts a story. | screenshot, index.html clock layer |
| Clock (idle) | H7, C1 | Month and clock are #57544F on #0B0B0A, 2.61:1. This fails even the 3:1 large text floor. The weekday is 3.66:1, under the H7 floor. | styles.css:228, styles.css:234, styles.css:221 |
| Clock (idle) | K2 | The month is italic. | screenshot |
| Recording | K2 | "te escucho" and the prompt are italic. | index.html:40, styles.css:185 |
| Recording | H1, H9 | The screen does not say how to stop and send. | screenshot |
| Recording | H3, H4 | A second tap within 650 ms cancels the story and replays the last one. A shaky double tap loses her story with no undo. | js/main.js:12, hearth-web/README.md (States and taps) |
| Clock (idle) | H3 | Double tap replays the last story. It is a hidden gesture with no visible path. | hearth-web/README.md (States and taps) |
| Sending | K2 | "guardando tu historia" is italic. | screenshot |
| Waiting | K1, K6 | "DOMINGO 25, 12:26" is an upper case eyebrow above the title. | js/main.js:78, styles.css:170 |
| Waiting | K2 | The subtitle is italic. | styles.css:185 |
| Waiting, Error | H6 | The label is 6u (24 px), below the 8u floor. | styles.css:169 |
| Waiting | W4, H1 | With no story title, the line says "presiona el boton para escucharla". The current build has no button. With a title, no line says what a tap does. | js/main.js:81 |
| Playing | K2 | "tu historia, sabado 24" is italic. | styles.css:351 |
| Playing | C3, H12 | The heading over a bright scene measures about 2.1:1 to 2.4:1, with the current text shadow. The top of the strip has only a light gradient. | screenshot, sampled pixels, styles.css:345 |
| Error | K1, K6 | "UN MOMENTO" is an upper case eyebrow above the message. | screenshot |
| Error | H10, A5 | The error goes back to the clock after 3.5 s, before a slow reader can read it twice. | js/main.js:17 |
| All | A1 | The strip is the only control, but it has no button role and no accessible name. A screen reader does not announce record or play. Taps come from a window pointerdown listener. | index.html:18, js/main.js:165 |
| All | T3 | The viewport sets maximum-scale=1 and user-scalable=no, so the user cannot zoom. | index.html:9 |

### Hearth on iOS (HearthView, role elder)

RootView still sends role elder to HearthView
(ios/MotherTongue/App/MotherTongueApp.swift:28).

| Rule | What is wrong | Proof |
| --- | --- | --- |
| H14, N1, N5 | Settings open only with a 1 s long press on a gear at 30 percent opacity. | Views/Hearth/HearthView.swift:194 |
| C2 | The gear icon is white at 0.3 opacity on a dark scene, under 3:1. | Views/Hearth/HearthView.swift:191 |
| K2 | The story title is italic. | Views/Hearth/HearthView.swift:99 |
| K3, K4 | SF Pro text, SF Symbols, gradient fills, and a capsule button. This is not the Kinn paper and serif style. | Views/Hearth/HearthView.swift:138, 165, 172, 178, 236 to 250 |
| K7, M1 | Repeating glow and scale animations and a spring press do not check Reduce Motion. | Views/Hearth/HearthView.swift:85, 129, 154 |
| T2 | Font.display uses fixedSize, so the elder screen does not follow Dynamic Type. | Views/Common/Theme.swift:58 |

### Almanac (iOS)

| Screen | Rule | What is wrong | Proof |
| --- | --- | --- | --- |
| All | K2 | English lines use Instrument Serif italic (serifItalic) on about 25 lines. | grep serifItalic in ios/MotherTongue/Views |
| All | K1, K6 | Inter tiny caps (tinyCaps) labels in upper case, used as eyebrows and labels on every screen. | Views/Common/Theme.swift:65 |
| Almanac | C1 | Tiny caps default to fog on paper, 2.82:1. Future days use later, 1.63:1. | Views/Family/AlmanacView.swift:56, 76 |
| Almanac | T1 | Week row weekday labels are 10 pt, below the 11 pt floor. | Views/Family/AlmanacView.swift:76 |
| Almanac | L8, C1 | "Settings" is a tiny caps fog label. It does not look like a control and fails contrast. | Views/Family/AlmanacView.swift:57 |
| Entry | L8 | "Close" is a tiny caps label on video, styled the same as static labels. | Views/Family/EntryView.swift:117 |
| Onboarding | C1 | The demo note is #9C968D on paper, 2.41:1. | Views/Onboarding/OnboardingFlow.swift:208 |
| Several | C1 | sub (#77726B, 3.91:1) and soft (#6F6B65, 4.34:1) on paper fail for text under 18 pt. Text in these colors at 18 pt and up passes. | Views/Family/AlmanacView.swift:104 (11 pt), :173 (17 pt); Views/Common/SettingsView.swift:85 (17 pt), :120 (16 pt); Views/Onboarding/OnboardingFlow.swift:207 (17 pt); Views/Onboarding/VoiceEnrollView.swift:32, :53 (17 pt) |
| Write back | N2, N5 | Recording works only with press and hold. There is no single tap path and no accessibility action. A press under 0.8 s throws the recording away. This is the required reply path. | Views/Family/WriteBackView.swift:125, :146, :173 |

## Sources

| Key | Source |
| --- | --- |
| AG | AGENTS.md in this repository |
| DS | design/DESIGN.md in this repository |
| EK | Emil Kowalski, design engineering skills: https://github.com/emilkowalski/skills |
| JK-UI | Jakub Krehel, better-ui: https://github.com/jakubkrehel/skills |
| JK-LAYOUT | Jakub Krehel, better-layout: https://github.com/jakubkrehel/skills |
| JK-TYPE | Jakub Krehel, better-typography: https://github.com/jakubkrehel/skills |
| HIG-ACC | https://developer.apple.com/design/human-interface-guidelines/accessibility |
| HIG-LAY | https://developer.apple.com/design/human-interface-guidelines/layout |
| HIG-TYP | https://developer.apple.com/design/human-interface-guidelines/typography |
| HIG-MOT | https://developer.apple.com/design/human-interface-guidelines/motion |
| HIG-HAP | https://developer.apple.com/design/human-interface-guidelines/playing-haptics |
| HIG-PROG | https://developer.apple.com/design/human-interface-guidelines/progress-indicators |
| HIG-GES | https://developer.apple.com/design/human-interface-guidelines/gestures |
| AND-48 | https://support.google.com/accessibility/android/answer/7101858 |
| W-1.2.2 | https://www.w3.org/WAI/WCAG22/Understanding/captions-prerecorded.html |
| W-1.4.1 | https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html |
| W-1.4.3 | https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html |
| W-1.4.4 | https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html |
| W-1.4.10 | https://www.w3.org/WAI/WCAG22/Understanding/reflow.html |
| W-1.4.11 | https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html |
| W-2.2.1 | https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html |
| W-2.3.1 | https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html |
| W-2.3.3 | https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html |
| W-2.4.7 | https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html |
| W-2.4.11 | https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html |
| W-2.5.1 | https://www.w3.org/WAI/WCAG22/Understanding/pointer-gestures.html |
| W-2.5.5 | https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html |
| W-2.5.7 | https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html |
| W-3.3.1 | https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html |
| NNG-RT | https://www.nngroup.com/articles/response-times-3-important-limits/ |
| NNG-SKEL | https://www.nngroup.com/articles/skeleton-screens/ |
| NNG-EMPTY | https://www.nngroup.com/articles/empty-state-interface-design/ |
| NNG-ERR | https://www.nngroup.com/articles/error-message-guidelines/ |
| NNG-SEN | https://www.nngroup.com/articles/usability-for-senior-citizens/ |
| NNG-MOB | https://www.nngroup.com/articles/mobile-usability-2nd-study/ |
| WAI-OLD | https://www.w3.org/WAI/older-users/ |
| SM-THUMB | https://www.smashingmagazine.com/2016/09/the-thumb-zone-designing-for-mobile-users/ |
| AMZ-MM | https://developer.amazon.com/en-US/alexa/alexa-haus/multimodal-introduction |
| LUX-FITTS | https://lawsofux.com/fittss-law/ |
| LUX-HICK | https://lawsofux.com/hicks-law/ |
| LUX-JAKOB | https://lawsofux.com/jakobs-law/ |
| LUX-MILLER | https://lawsofux.com/millers-law/ |
| LUX-DOHERTY | https://lawsofux.com/doherty-threshold/ |
| LUX-TESLER | https://lawsofux.com/teslers-law/ |
| LUX-AESTH | https://lawsofux.com/aesthetic-usability-effect/ |
| LUX-PEAK | https://lawsofux.com/peak-end-rule/ |
| LUX-VONR | https://lawsofux.com/von-restorff-effect/ |
| LUX-SERIAL | https://lawsofux.com/serial-position-effect/ |
| LUX-GOAL | https://lawsofux.com/goal-gradient-effect/ |
| LUX-ZEIG | https://lawsofux.com/zeigarnik-effect/ |
| LUX-PROX | https://lawsofux.com/law-of-proximity/ |
| LUX-REGION | https://lawsofux.com/law-of-common-region/ |
| LUX-POSTEL | https://lawsofux.com/postels-law/ |
| REF-THINGS | https://culturedcode.com/things/features/ |
| REF-DAYONE | https://ixd.prattsi.org/2026/09/design-critique-day-one-iphone-app/ |
| REF-DUO | https://blog.duolingo.com/streak-milestone-design-animation |
| REF-HEAD | https://dribbble.com/stories/2020/03/27/headspace-design-karen-hong |
| REF-AIRBNB | https://news.airbnb.com/airbnb-2023-winter-release/ |
| REF-JOURNAL | https://www.macstories.net/reviews/apples-journal-app-journaling-for-all/ |
