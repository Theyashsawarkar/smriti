# Changelog

Newest first. Releases are tags (`vX.Y.Z`).

## v0.2.0 -- 2026-10-24

- The filter tabs switch like every Vyom tool's tabs (Vyom 0.3.0): `Ctrl+H` / `Ctrl+L`
  for the previous / next, `Ctrl+1..5` by number as before. Needs Vyom 0.3.0.

## v0.1.4 -- 2026-10-21

- A website (GitHub Pages, https://theyashsawarkar.github.io/smriti/): the README as a home page, the
  changelog, and architecture decision records (`docs/adr/`), built from these files by
  `scripts/build-site.py`; CI checks the site is up to date.

## v0.1.3 -- 2026-10-21

- Documentation for open source: a logo and banner, a full README (features,
  install, usage, configuration, troubleshooting, the whole Vyom family),
  CONTRIBUTING, SECURITY and CODE_OF_CONDUCT, issue and pull request
  templates, and CI (compiles, checks plugin.toml and that every key is
  documented).

## v0.1.2 -- 2026-10-19

- Opens at Vyom's shared panel size (Vyom 0.2.5) like every other tool:
  its own width/height are gone.

## v0.1.1 -- 2026-10-19

- Keys are spelled out (Ctrl+Enter, Shift+Enter, Backspace) instead of symbols
  (⌃↵, ⇧↵, ⌫) in the footer and on rows and buttons.

## v0.1.0 -- 2026-10-19

- First release, as its own repository: clipboard history. Replaces `cliphist list | wofi --dmenu` in Vayu.
- Your cliphist history, each entry recognised as a **link, image, code, command, email or text**, with a filter tab for each.
- A full preview: the whole text (not cliphist's cut-off line), link domains, and **images as pictures**.
- `Enter` copies; `Ctrl+Enter` copies and pastes into the window you were in.
- **Pin** what you reuse (`Ctrl+P`); delete what shouldn't be kept (`Delete`).
