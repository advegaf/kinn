# Hearth design system: Almanac (v4c, locked)

Source of truth: `design/iterations/v4c/index.html` and `design/iterations/v4c/board.png`. When this file and the mockup disagree, the mockup wins; fix this file.

## Thesis

The week is a page in an almanac. Big serif numerals, ruled lines, cream paper, one oxblood ribbon marking today. No photos in the archive; the story film shows up only when you open an entry or when the Hearth plays it. The Hearth idle screen is the same day numeral, set large on night. The object (a matte taupe or cream shell) does the decorating, so the screen stays quiet.

Rules that follow from it:

- One accent at a time. Oxblood ribbon on paper, lamp-white light on the Hearth button, muted red only for REC.
- No mint anywhere. Earlier plans mention a mint glow (`#A8F0CF`); it is dropped.
- No pills, chips, cards, gradients on UI, spinners, bouncing or sliding. Fades only.
- Spanish first, English beneath it in italic, smaller and greyer.

## Color tokens

| Token | Hex | Role |
| --- | --- | --- |
| `cream` | `#ECE6DC` | Shell color; primary text on night |
| `paper` | `#EEE8DE` | iPhone page background (light screens) |
| `studio` | `#E2DED8` | Backdrop behind devices in mockups only; never in product |
| `taupe` | `#CFC6B8` | Hearth shell, mini Hearth illustration |
| `shell-rim` | `#C4BBAC` | Ring around the Hearth glass, mini Hearth display rim |
| `button-cap` | `#C8BFB1` | Unlit Hearth button cap |
| `fog` | `#8E8A84` | Secondary text on night, tiny labels, counters' colon, timestamps |
| `soft` | `#6F6B65` | Secondary text on paper (past day numerals, hints, quotes) |
| `sub` | `#77726B` | English italic subtitles on paper |
| `faint` | `#A39D94` | Inactive prompt lines on paper; on night use `#A39E96` for italic links |
| `later` | `#BDB7AE` | Future days (not yet happened) on paper |
| `ink` | `#1B1A18` | Primary text on paper, primary button fill |
| `night` | `#0B0B0A` | Hearth strip, iPhone playback screen |
| `night-text` | `#D9D3C9` | Body text on night (story words) |
| `ribbon` | `#82342C` | Oxblood ribbon bookmark, stamp ink, active roman numeral |
| `madder` | `rgba(140,59,50,.26)` | Margin rule, quote rule on paper |
| `rule` | `rgba(27,26,24,.13)` | 1px ruled lines on paper |
| `rec` | `#B23A2E` | REC dot, record disc center |
| `rec-label` | `#C9584B` | REC text on night (Hearth) |
| `lamp` | `#F6E7C8` | Lamp-white button light. Gradient `#FFF8EA 0`, `#F8EBD0 38%`, `#EBD9B6 72%`, `#D9C7A6 100%` |
| `cell` | `#E2DACD` on paper, `#1C1B19` on night | Flip counter cells |

Hearth idle numerals are dimmed fog tones, not cream: numeral `#8A867F`, weekday `#6E6A64`, month and clock `#57544F`.

Track bar on night: base `rgba(236,230,220,.18)`, fill `rgba(236,230,220,.75)`, 1px tall.

## Type

Two families. Nothing else.

- Serif: Instrument Serif, regular and italic, weight 400 only. iOS uses Instrument Serif bundled; New York is the fallback. Web stack `"Instrument Serif", "New York", Georgia, serif`.
- Sans: Inter, weights 300, 400, 500, for tiny labels and the big tape counter only. iOS fallback SF Pro.
- Never synthesize italic: load the real italic face.
- `font-variant-numeric: tabular-nums` (iOS `.monospacedDigit()`) on every numeral that changes or aligns: day numerals, clocks, counters, track times, codes.
- Smoothing: antialiased (web `-webkit-font-smoothing: antialiased`).

### Tiny label (the "mono" label, though it is Inter)

Inter 400, 11px, line-height 1, tracking .08em, uppercase, `fog`, no wrap. Variants: weekday row 10px at .1em; stamp 9.5px weight 500 at .12em; REC 11px weight 500 at .12em in `rec`. On the Hearth strip: 24px at .08em.

### iPhone scale (points, 393 wide screen)

| Role | Face | Size / line-height | Tracking | Color |
| --- | --- | --- | --- | --- |
| Month display ("octubre") | Serif | 66 / .95 | -.025em | ink |
| Page title ("Para Abuela Rosa") | Serif | 52 / 1.02 | -.025em | ink |
| Day numeral, playback header | Serif | 80 / .8 | -.03em | cream |
| Week row numerals | Serif | 40 / 1 | 0 | soft, today ink, later `later` |
| Featured title | Serif | 34 / 1.02 | -.015em | ink |
| Entry title on night | Serif | 32 to 36 / 1.02 | -.015em | cream |
| Live transcript | Serif | 32 / 1.2 | -.01em | ink, unconfirmed words `#A9A39A` |
| Code digits | Serif | 58 / 1 | 0 | ink |
| Field value | Serif | 26 / 1 | 0 | ink |
| Index row title | Serif | 19 / 1.1 | 0 | ink |
| Index row English | Serif italic | 17 / 1.1 | 0 | sub |
| Index row day number | Serif | 22 / 1 | 0 | fog |
| English subtitle under display | Serif italic | 19 to 20 | 0 | sub |
| Story body on night | Serif | 21 / 1.4, `text-wrap: pretty` | 0 | night-text, italic run `#A39E96` |
| Links ("Hear her original") | Serif italic | 19 to 20 / 1 | 0 | soft (paper) or `#A39E96` (night); dotted 1px underline, offset 5px |
| Primary text action ("Listen") | Serif italic | 19 | 0 | ink, dotted underline |
| Hint ("Let go to send") | Serif italic | 18 / 1 | 0 | soft |
| Tape counter (big) | Inter 300 | 46 / 1 | -.01em | ink, colon fog |
| CTA button label | Serif | 21 / 1 | 0 | cream on ink, 58 tall, radius 4 |

Headings use `text-wrap: balance`. Italic English subtitle sits 6 to 10 below its Spanish line.

### Hearth scale

Hearth frames are authored at 1280 x 400, which is exactly the default strip on the Fire HD 8 (1280 x 800 screen, strip 25% to 75% high). Web sizes are in `u`, where 1u = 1% of strip height (4px at default), so a recalibrated strip scales everything.

| Role | Face | px at 1280x400 | u | Line-height | Tracking | Color |
| --- | --- | --- | --- | --- | --- | --- |
| Idle day numeral ("24") | Serif | 290 | 72.5 | .8 | -.04em | `#8A867F` |
| Idle weekday ("sábado") | Serif | 64 | 16 | 1 | 0 | `#6E6A64` |
| Idle month ("octubre") | Serif | 46 | 11.5 | 1 | 0 | `#57544F`, 12px below weekday |
| Idle clock ("7:42") | Serif | 110 | 27.5 | 1 | 0 | `#57544F`, right aligned |
| Waiting label ("SÁBADO 24, 7:42") | Inter 400 caps | 24 | 6 | 1 | .08em | fog |
| Waiting headline ("Sofía te escribió") | Serif | 112 | 28 | 1 | -.02em | cream, 22px below label |
| Waiting sub ("sobre «...»") | Serif italic | 46 | 11.5 | 1.1 | 0 | fog, 16px below |
| Recording headline ("te escucho") | Serif italic | 116 | 29 | 1 | -.02em | cream |
| Recording prompt | Serif italic | 44 | 11 | 1.1 | 0 | fog, 18px below |
| REC label | Inter 500 caps | 24 | 6 | 1 | .12em | `#C9584B`, dot 22px `rec`, gap 16 |
| Flip counter digits | Inter 400 | 52 | 13 | 1 | 0 | cream, colon fog |
| Flip counter cell | | 52 x 76, radius 8, gap 6 | 13u x 19u | | | `#1C1B19`, inset shadow `0 2px 6px rgba(0,0,0,.7)`, top hairline `0 1px 0 rgba(255,255,255,.06)` |
| Playing stamp ("de Sofía, sábado 24") | Serif italic | 44 | 11 | 1 | 0 | `rgba(236,230,220,.82)`, at left 90, top 56 |
| Playing caption | Serif | 56 | 14 | 1.1 | 0 | cream, shadow `0 2px 30px rgba(0,0,0,.6)`, left 90, right 160, bottom 60, balance |

Hearth layout: side padding 120px (30u); idle row is numeral, then weekday stack 40px to its right (padding-left 110px), clock pushed to the far right. Waiting is a left aligned column, vertically centered. Recording is headline column left, REC plus counter right aligned on the right, 26px apart.

## Texture

- Grain over every surface, paper and night: SVG `feTurbulence type=fractalNoise baseFrequency=.8 numOctaves=3 stitchTiles=stitch`, desaturated, 240px tile, `mix-blend-mode: overlay`, opacity .5. On iOS use a pre-rendered 240px noise PNG with overlay blend at .5 (or .35 on paper if it reads dirty on device).
- Vignette on night screens: `radial-gradient(120% 90% at 50% 40%, transparent 55%, rgba(0,0,0,.5))`.
- Film vignette (playing): `radial-gradient(90% 120% at 50% 50%, transparent 45%, rgba(0,0,0,.7))`. Media filter `saturate(.85) brightness(.82)`.
- Paper binding: left edge shadow 26px wide, `linear-gradient(90deg, rgba(70,52,34,.16), rgba(70,52,34,.05) 40%, transparent)`. Fore edge: 5px of 1px stripes `rgba(90,72,52,.12)` every 2px.
- Prints (story stills on paper): `saturate(.82) contrast(.96)`, inner shadow `inset 0 0 30px rgba(30,24,18,.3)`, radius 2.

## Ruled lines

1px `rule` lines between every row (week, index, fields, prompts). Rows: 10 to 13 top, 9 to 11 bottom. Grid of label column then content: 44px for index day numbers, 96px for field labels and day names, 30px for roman numerals (i, ii, iii). Optional madder margin rule: 1px vertical `madder` at the label column edge. No boxes, no fills, no rounded containers.

## Components

### Ribbon bookmark

The only mark for "today" or "new" on paper. 17px wide, hangs from the top edge of the screen onto today's numeral (238px long on the week screen, centered on the today column). Fill `ribbon` with woven texture layers: top shade `linear-gradient(180deg, rgba(0,0,0,.28), transparent 14px)`, side shade 14% black at both edges, a 1px highlight 9px from the top `rgba(255,235,225,.14)`, vertical threads `rgba(255,236,224,.09)` 1px every 2.5px, horizontal threads `rgba(0,0,0,.11)` 1px every 2px. Swallowtail notch: `clip-path: polygon(0 0, 100% 0, 100% 100%, 50% calc(100% - 9px), 0 100%)`. Shadow `drop-shadow(0 3px 2px rgba(40,18,10,.32))` plus `drop-shadow(1px 0 0 rgba(40,18,10,.12))`.

### Dater stamp (optional)

Inter 500 9.5px, .12em, caps, `ribbon`, 1px border radius 3, padding 5/6/4, rotated -2.5deg, opacity .78, masked with the grain tile at 120px so the ink looks pressed.

### REC dot plus tape counter

REC: dot (8px on phone, 22px on Hearth) in `rec`, then "REC" in Inter 500 caps .12em. Counter `MM:SS`, tabular. Phone big counter is Inter 300 46px, colon in fog. Hearth and small phone counter use flip cells: each digit in its own cell (phone 19 x 26 radius 3 `#E2DACD`, inset `0 1px 2px rgba(60,44,28,.22)`, bottom highlight `0 1px 0 rgba(255,255,255,.7)`; Hearth values above). The colon sits between cells in fog with 1px padding. Digits change instantly, no flip animation.

### Lamp button (Hearth)

Physical cap seen through the shell. Unlit: `button-cap` with `inset 0 6px 12px rgba(70,58,44,.35)`. Lit (new story waiting): radial `circle at 50% 46%` of the lamp gradient above, outer halo `0 0 0 3px rgba(246,231,200,.35), 0 0 16px 2px rgba(246,231,200,.38)`. On the Fire, the light is a radial spot drawn under the button zone: `#FFF8EA` center to `#F6E7C8` to transparent. Idle opacity about .12, waiting breathes .35 to .8 over 7s ease-in-out alternate, recording and playing stay dark-dim (the cap reads pressed). Never saturated orange, never mint.

### Big date numeral

The Hearth idle hero and the playback header: Serif regular, tabular, very tight leading (.8) and negative tracking (-.03 to -.04em), with weekday and month stacked to its right in smaller serif. The numeral is today's day of month, never a time.

### Record disc (phone)

72px circle `ink`, center dot 22px `rec`, shadows `inset 0 -2px 4px rgba(0,0,0,.4), 0 10px 18px -10px rgba(30,20,10,.5)`. Press scales to .97 over 160ms ease-out.

## Motion

Dream Recorder timings. Fades only, opacity, no translation, no scale on content.

- Enter: 500ms `cubic-bezier(0.23, 1, 0.32, 1)`. Exit faster: 250ms, same curve.
- Media crossfades (story film in or out, vignette, Hearth state to playing): 2s ease-out in, 500ms out.
- Lamp breathe: 7s ease-in-out alternate, infinite.
- Sending ("guardando tu historia"): one slow opacity breathe on the line, 2.4s alternate between .55 and 1. Nothing spins.
- Ken Burns on stills during playback: scale 1.04 to 1.16 over 14s linear, crossfade 1.6s.
- Reduced motion: keep fades, drop Ken Burns and the breathe (hold the lamp at .7).
- Press feedback on phone controls: scale .97, 160ms ease-out. On the Hearth the physical button is the feedback; the screen only changes state.

## Copy

Spanish on the Hearth, always. Partner name comes from data (`partner.name`). Lowercase serif for calm lines ("te escucho", "guardando tu historia"). Tiny caps labels are written in natural case and uppercased by style. Guillemets for titles: «Los tamales de mamá». Straight quotes in code. No dashes of any length in copy.

## Do

- Let one big serif numeral or headline own each screen.
- Use ruled lines and the label column for structure.
- Keep color for meaning: ribbon is today, lamp is "something waiting", red is "recording".
- Put the English under the Spanish, italic, smaller, greyer.
- Keep everything outside the Hearth strip black, except the lamp spot.

## Don't

- No mint, no saturated orange, no gradients on UI chrome.
- No pills, chips, badges, cards, drop shadows on text blocks (caption text shadow on film is the only one).
- No spinners, progress dots, bouncing, sliding, or scaling content in.
- No third typeface (Ballet, Geist Mono and Inter display headlines are gone).
- No bold serif. Instrument Serif is 400 only.
- No photos in the archive list. Film appears only in the entry and on the Hearth.
