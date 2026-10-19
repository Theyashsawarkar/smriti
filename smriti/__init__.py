"""smriti (स्मृति, "memory"): clipboard history for Vyom, over cliphist.

Every entry is recognised as a link, an image, code, a command, an email
address or text, with a filter tab for each kind and a full preview
(images as pictures). Pin what you reuse; delete what shouldn't be kept.
"""
import os
import re
import subprocess

from gi.repository import Gtk

from vyom import Hint, Row, Section, ui, util
from vyom import Plugin as Base

# keybind: Vyom/clipboard | Enter | Copy the selected entry
# keybind: Vyom/clipboard | Ctrl+Enter | Copy and paste the selected entry
# keybind: Vyom/clipboard | Ctrl+P | Pin or unpin the selected entry
# keybind: Vyom/clipboard | Delete / Ctrl+Backspace | Delete the selected entry from the history
# keybind: Vyom/clipboard | Ctrl+1..5 | Show all, text, images, links or code

PINS = "smriti-pins"
IMG = re.compile(r"^\[\[ binary data ([\d.]+ \w+) (\w+) (\d+x\d+) \]\]$")
CMD = re.compile(r"^(sudo |git |docker |npm |pnpm |yarn |cd |ls |cat |curl |ssh |pacman |systemctl |make |python3? |pip |kubectl |gh |cargo )")
CODE = re.compile(r"^\s*<[a-zA-Z!?]|[{};]\s*$|=>|\bfunction\b|\bdef |\bconst |\blet |\bimport |\bclass |</?\w+[^>]*>", re.M)
KINDS = {  # kind: (icon, color, label)
    "link": ("\U000f0337", "blue", "Link"),
    "image": ("\U000f02e9", "mauve", "Image"),
    "code": ("\U000f0169", "green", "Code"),
    "command": ("", "gray", "Command"),
    "email": ("\U000f01ee", "peach", "Email"),
    "text": ("\U000f0219", "teal", "Text"),
}
TABS = [("all", "All"), ("text", "Text"), ("image", "Images"), ("link", "Links"), ("code", "Code")]


def kind_of(preview):
    p = preview.strip()
    if IMG.match(p):
        return "image"
    if re.match(r"^https?://\S+$", p):
        return "link"
    if re.match(r"^[\w.+-]+@[\w-]+\.[\w.]+$", p):
        return "email"
    if CMD.match(p) or p.startswith("$ "):
        return "command"
    if CODE.search(p):
        return "code"
    return "text"


def decode(line):
    try:
        return subprocess.run(["cliphist", "decode"], input=line.encode(), capture_output=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return b""


class Plugin(Base):
    name, title, icon, color = "smriti", "Clipboard", "\U000f014c", "teal"
    placeholder = "Search the clipboard…"
    preview = True
    preview_width = 320
    width = 760
    hints = [Hint("Enter", "copy"), Hint("Ctrl+Enter", "paste"), Hint("Ctrl+P", "pin"), Hint("Del", "delete")]
    empty_text = "The clipboard history is empty"

    def __init__(self, vyom, conf):
        super().__init__(vyom, conf)
        self.tab = "all"
        self.tab_buttons = {}

    def header_extra(self):
        box = Gtk.Box(spacing=4)
        group = None
        for key, label in TABS:
            b = Gtk.ToggleButton(label=label)
            b.add_css_class("tab")
            if group is None:
                group = b
                b.set_active(True)
            else:
                b.set_group(group)
            b.connect("toggled", lambda btn, k=key: btn.get_active() and self.set_tab(k))
            b.set_can_focus(False)
            self.tab_buttons[key] = b
            box.append(b)
        return box

    def set_tab(self, key):
        self.tab = key
        self.refresh()

    def search(self, q):
        code, out = util.run(["cliphist", "list"], timeout=5)
        entries = []
        for line in out.splitlines() if code == 0 else []:
            if "\t" not in line:
                continue
            cid, prev = line.split("\t", 1)
            entries.append((line, cid, prev, kind_of(prev)))
        pins = util.load_state(PINS, {"items": []})["items"]
        rows = []
        if pins and self.tab == "all" and not q:
            rows.append(Section("Pinned"))
            for p in pins:
                rows.append(Row(p["text"].splitlines()[0][:200] if p["text"] else "", "pinned", icon="\U000f0403",
                                color="yellow", data={"pin": p}))
        shown = []
        for line, cid, prev, kind in entries:
            if self.tab != "all" and kind != self.tab and not (self.tab == "text" and kind in ("email", "command")):
                continue
            if q and util.fuzzy(q, prev) is None:
                continue
            shown.append(self.row(line, cid, prev, kind))
            if len(shown) >= 300:
                break
        if shown:
            if rows:
                rows.append(Section("History"))
            rows += shown
        return rows

    def row(self, line, cid, prev, kind):
        icon, color, label = KINDS[kind]
        m = IMG.match(prev.strip())
        title = f"Image {m.group(3)}" if m else prev.strip().replace("\n", " ")[:200]
        sub = f"{label} · {m.group(2)} · {m.group(1)}" if m else label
        return Row(title, sub, icon=icon, color=color, meta=f"#{cid}", data={"line": line, "id": cid, "kind": kind,
                                                                          "preview": prev})

    # ------------------------------------------------------------ preview
    def image_path(self, cid):
        return os.path.join(util.CACHE, "smriti", f"{cid}.img")

    def build_preview(self, row):
        d = row.data
        if "pin" in d:
            return ui.vbox(ui.chip("Pinned", "yellow"), ui.mono(d["pin"]["text"][:3000]),
                           ui.buttons([("Copy", lambda: (util.copy(d["pin"]["text"]), self.close())),
                                       ("Unpin", lambda: self.unpin(d["pin"]["text"]))]), spacing=10)
        icon, color, label = KINDS[d["kind"]]
        parts = [ui.hbox(ui.chip(label, color), ui.meta(f"entry #{d['id']}"), spacing=8)]
        if d["kind"] == "image":
            path = self.image_path(d["id"])
            if os.path.exists(path):
                parts.append(ui.picture(path, 200))
            else:
                parts.append(ui.meta("loading…"))
                self.background(lambda: self.cache_image(d), lambda _r: self.panel.update_preview_soon())
            m = IMG.match(d["preview"].strip())
            if m:
                parts.append(ui.kv([("Size", m.group(3)), ("Format", m.group(2).upper()), ("Bytes", m.group(1))]))
        else:
            text = d["preview"]
            if len(text) >= 90 or "\n" in text:  # cliphist's preview is cut: get the whole thing
                full = decode(d["line"]).decode("utf-8", "replace")
                text = full or text
            if d["kind"] == "link":
                parts.append(ui.title(re.sub(r"^https?://([^/]+).*$", r"\1", text.strip())))
            parts.append(ui.mono(text[:3000] + ("…" if len(text) > 3000 else "")))
            parts.append(ui.meta(f"{len(text)} characters · {text.count(chr(10)) + 1} lines"))
        parts.append(ui.buttons([("Copy", lambda: self.copy_entry(d), "primary"), ("Pin", lambda: self.pin(d)),
                                 ("Delete", lambda: self.delete(d), "danger")]))
        return ui.vbox(*parts, spacing=10)

    def cache_image(self, d):
        os.makedirs(os.path.join(util.CACHE, "smriti"), exist_ok=True)
        data = decode(d["line"])
        if data:
            with open(self.image_path(d["id"]), "wb") as f:
                f.write(data)

    # ------------------------------------------------------------ actions
    def copy_entry(self, d, paste=False):
        data = decode(d["line"])
        if not data:
            return
        subprocess.run(["wl-copy"], input=data, timeout=5)
        self.close()
        if paste and util.have("wtype"):
            subprocess.Popen(["sh", "-c", "sleep 0.15; wtype -M ctrl -k v -m ctrl"])

    def pin(self, d):
        text = decode(d["line"]).decode("utf-8", "replace") if d.get("kind") != "image" else ""
        if not text:
            util.notify("Clipboard", "Images can't be pinned")
            return
        pins = util.load_state(PINS, {"items": []})
        if not any(p["text"] == text for p in pins["items"]):
            pins["items"].insert(0, {"text": text})
            util.save_state(PINS, {"items": pins["items"][:30]})
        self.refresh()

    def unpin(self, text):
        pins = util.load_state(PINS, {"items": []})
        util.save_state(PINS, {"items": [p for p in pins["items"] if p["text"] != text]})
        self.refresh()

    def delete(self, d):
        if "line" in d:
            subprocess.run(["cliphist", "delete"], input=d["line"].encode(), timeout=5)
            try:
                os.unlink(self.image_path(d["id"]))
            except OSError:
                pass
        self.refresh()

    def activate(self, row, mods):
        d = row.data
        if "pin" in d:
            util.copy(d["pin"]["text"])
            return True
        self.copy_entry(d, paste="ctrl" in mods)
        return False

    def key(self, name, row, mods):
        if row is None:
            return False
        if name == "p" and "ctrl" in mods:
            self.unpin(row.data["pin"]["text"]) if "pin" in row.data else self.pin(row.data)
            return True
        if name == "Delete" or (name == "BackSpace" and "ctrl" in mods):
            self.unpin(row.data["pin"]["text"]) if "pin" in row.data else self.delete(row.data)
            return True
        if "ctrl" in mods and name in "12345" and len(name) == 1:
            key = TABS[int(name) - 1][0]
            self.tab_buttons[key].set_active(True)
            return True
        return False
