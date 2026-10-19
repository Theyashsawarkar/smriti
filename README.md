# smriti

**smriti** (स्मृति, "memory") — Clipboard history. A tool for [Vyom](https://github.com/Theyashsawarkar/vyom), the keyboard-driven panels of [Vayu](https://github.com/Theyashsawarkar/vayu); in Vayu it replaces `cliphist list | wofi --dmenu`.

> Clipboard history (cliphist): links, images, code and commands told apart, a full preview, pins, delete.

## Features

- Your cliphist history, each entry recognised as a **link, image, code, command, email or text**, with a filter tab for each.
- A full preview: the whole text (not cliphist's cut-off line), link domains, and **images as pictures**.
- `Enter` copies; `Ctrl+Enter` copies and pastes into the window you were in.
- **Pin** what you reuse (`Ctrl+P`); delete what shouldn't be kept (`Delete`).

## Keys

| Key | Action |
|---|---|
| `Enter` | Copy the selected entry |
| `Ctrl+Enter` | Copy and paste the selected entry |
| `Ctrl+P` | Pin or unpin the selected entry |
| `Delete / Ctrl+Backspace` | Delete the selected entry from the history |
| `Ctrl+1..5` | Show all, text, images, links or code |
| `Esc` | close |

Every Vyom panel also has: `Up`/`Down` (or `Ctrl+K`/`Ctrl+J`) to move, `Page Up`/`Page Down`, `Tab` to switch to the next tool.

## Requirements

- [Vyom](https://github.com/Theyashsawarkar/vyom) 0.2 or newer (Python 3.11+, GTK 4, gtk4-layer-shell, a layer-shell compositor)
- `cliphist`, `wl-copy`
- optional: wtype (Ctrl+Enter paste)

## Install

```sh
git clone https://github.com/Theyashsawarkar/smriti ~/.local/share/vyom/plugins/smriti
vyom reload        # or log out and in
vyom smriti         # open it (again: close it)
```

Bind it to a key, e.g. in sway:

```
bindsym $mod+<key> exec vyom smriti
```

Update: `git -C ~/.local/share/vyom/plugins/smriti pull && vyom reload`. `vyom list` shows every installed tool and why one would be skipped.

## License

MIT.
