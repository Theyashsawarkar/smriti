# Changelog

Newest first. Releases are tags (`vX.Y.Z`).

## v0.4.0 -- 2026-11-09

- `Space u p` (show or hide the preview) now comes from Vyom core, which also remembers it per tool; the tool's own copy is gone.
- **Vim keys** (Vyom 0.7, ADR 0008): NORMAL and INSERT modes, `Space` as the leader with a which-key strip, `?` and `Space ?` list every key, `Space Space` is a palette, counts (`5j`), `gg` / `G`, `H` / `L` for tabs. It opens in INSERT (search-first): type, then `Esc` for NORMAL. Needs Vyom 0.7.0.
- Its keys are data (`smriti/vim.py`); `scripts/keybinds.py` writes the `# keybind:` lines and the README's key tables from them, and `--check` (CI) fails when they drift.
- `p` pastes, `y y` copies and stays open, `m` pins, `d d` deletes (asks first, `y` deletes; it replaces pressing Delete twice), `Space d a` clears the history (pins stay), `Space o b` opens a link, `Space o e` opens an entry in $EDITOR, `Space y p` copies it trimmed, `Space u p` hides the preview.
- While typing, `Delete` and `Ctrl+C` belong to the search box again.
- The delete question names the entry (`Delete this link (https://…) …?`), so `y` never deletes one you didn't mean.

## v0.3.0 -- 2026-11-07

- **Grouped by time**: Pinned, Just now, Today, Yesterday and Older instead of a bare entry number, with
  an age on every row ("1 min", "11:20"). cliphist keeps no times, so smriti notes them while Vyom runs
  by watching the clipboard (`wl-paste --watch`; `track_times = false` turns it off). See docs/adr/0004.
- **Each kind has its own colour and icon**: link blue, code green, command peach, image mauve, text
  teal; the tabs use the same colours.
- **Images show as thumbnails** in the list, links show their site, code and commands are in a
  monospace font, and text says how many words it has.
- The preview colours code (keywords, strings, numbers, calls, comments), guesses its language, and
  says how long ago you copied it. Its buttons are Copy (`Enter`), Paste (`Ctrl+Enter`), Pin (`Ctrl+P`)
  and a red Delete (`Delete`).
- **Delete asks first**: it can't be undone, so the first `Delete` asks and the second (within 4 s)
  deletes. `Ctrl+Backspace` no longer deletes.
- `Ctrl+Enter` on a pinned entry pastes it too.
- Needs Vyom 0.6.0.
- Every corner is rounded: the website's callouts.
- A logo and a shloka at the top of the README and the website: every Vayu tool has them now.
- Screenshots in the README and on the website.

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
