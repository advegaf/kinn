# Agent guidance for this repository

These rules apply to every agent that works in this repository, Claude and
Codex alike. Read this file before you start a task.

## Project

- Kinn connects a grandparent and a grandchild who speak different
  languages. The Hearth is a framed screen in the grandparent's kitchen
  (hearth-web, shown by the Android kiosk app in fire-kiosk). The Almanac
  is the grandchild's iPhone app (ios/MotherTongue, SwiftUI).
- The backend is Supabase edge functions (backend/supabase). The story
  worker (story-worker, Python) makes the story beats and the Luma scenes.
- Built for HackTX 2026, Meta track. The README and docs/ explain the
  product, the contract (docs/CONTRACT.md), and the architecture
  (docs/ARCHITECTURE.md). Read the relevant doc before you design or build.
- The demo path must always work: Rosa records on the Hearth, the story is
  processed, Sofia opens and plays it in the Almanac, and writes back.
  Demo mode (hearth-web ?demo=1, DemoBackend.swift) must work with no keys.

## Quality gates

Check these gates yourself before every PR.

- Lines per file: less than 500. Split a file before it gets to 500.
  Existing files over the limit (story-worker/main.py, hearth-web/js/main.js,
  hardware/render/hearth_showcase.py) must not grow. Split them when you
  touch them.
- Cyclomatic complexity per function: less than 22.
- Dead code: 0. No unused functions, files, assets, or dependencies.
- Redundant code: 0. Search for an existing helper before you write a new
  one. Do not duplicate logic.
- No force unwraps (!) or try! in Swift outside DEBUG code.
- No secrets in the repo. Keys live in Supabase secrets, the gitignored
  .env files, and ios/Config/Secrets.xcconfig.

## Testing

- No tests written. Do not add unit tests or integration tests.
- The only exception is the end to end suite (issue 9). It drives the real
  Hearth and the real Almanac in demo mode.
- Prove a change works by running the app and looking at it, not by
  writing a test.

## Comments

- Comments are a cost. Default is no comment.
- Keep only a fact the reader cannot get from the code (an API quirk, an
  OS limit, a product decision).
- Delete comments that restate the code or that mark sections.

## Git

- Never push to main. Create a branch, push with git push -u origin, then
  open a PR.
- One issue per branch and per PR. Write "Closes #N" in the PR.
- Never add co-author attribution of any kind.
- Review the staged file list before committing. Drop unrelated files and
  scratch artifacts (screenshots, logs, build output).

## Writing style

- Use ASD-STE100 Simplified Technical English in comments, docs, commits,
  and PR text.
- Plain ASCII only. No emojis, no em dashes, no decorative formatting.
- Be simple, brief, and direct. Write for a non-native English speaker.

## UI work

These rules apply to every change that a person can see on the Hearth or
in the Almanac: layout, spacing, color, type, icons, focus, and motion.

- Follow docs/UI_STANDARD.md (issue 8) when it exists.
- Use two skill sets, and read the full skill file again each time you use
  it. A read from earlier in the session does not count.
  - Emil Kowalski: https://github.com/emilkowalski/skills
  - Jakub Krehel: https://github.com/jakubkrehel/skills (the better-* skills)
    and https://github.com/jakubkrehel/make-interfaces-feel-better
- No eyebrow headers. Do not put a small label (often upper case or letter
  spaced) above or beside a title or a section.
- No italicizing. Do not use italic type anywhere in the UI.
- No default Apple look for navigation and bars. Kinn has its own paper
  and serif style. Keep every new surface in that style.
- Touch targets are at least 44 pt. Respect safe areas, Dynamic Type, and
  Reduce Motion.
- The Hearth is for an older person: large type, one action at a time, no
  hidden gestures, and clear feedback after each action.
- Capitalize names and labels. Use sentence case for UI text.
- Do not crowd a screen with information. Show only what the person needs
  now.
- Study products with high UI standards and compare the screen against
  them.
- Spacing is a first class concern. Use one spacing scale. Check every
  padding, gap, and alignment against the neighbor elements.
- Check at pixel level. Run the app, take screenshots of small regions,
  zoom in, and find what is wrong: a 1 px shift, uneven padding, a color
  step, a clipped glyph. Fix it and check again.
