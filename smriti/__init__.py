"""smriti (स्मृति, "memory"): clipboard history for Vyom, over cliphist.

Every entry is recognised as a link, an image, code, a command, an email
address or text, each with its own colour and icon, and grouped by when
you copied it (Pinned, Just now, Today, Yesterday, Older). Images show as
thumbnails in the list, links show their site, and code gets syntax
colours in the preview. Pin what you reuse; delete what shouldn't be kept
(Delete twice: it can't be undone).

cliphist keeps no times, so smriti notes them: while Vyom runs it watches
the clipboard (`wl-paste --watch`) and gives cliphist's newest entry the
time of the copy; an entry it didn't see arrive gets the time it was first
listed, and the ones from before smriti watched none ("Older").
"""
import ctypes
import datetime
import os
import re
import shutil
import signal
import subprocess
import threading
import time

from gi.repository import GdkPixbuf, GLib, Gtk, Pango

from vyom import Hint, Row, Section, ui, util
from vyom import Plugin as Base

from . import vim

# KEYBINDS (generated from smriti/vim.py by scripts/keybinds.py; don't edit by hand)
# keybind: Vyom/smriti:insert | Enter | Copy the selected entry
# keybind: Vyom/smriti:insert | Ctrl+Enter | Paste the selected entry (copies it, then pastes into your window)
# keybind: Vyom/smriti:normal | Enter | Copy the selected entry and close
# keybind: Vyom/smriti:normal | p | Paste the selected entry into your window
# keybind: Vyom/smriti:normal | y y | Copy the selected entry and stay open
# keybind: Vyom/smriti:normal | m | Pin or unpin the selected entry
# keybind: Vyom/smriti:normal | d d | Delete the selected entry (a pinned one: unpin it; asks first)
# keybind: Vyom/smriti | Ctrl+P | Pin or unpin the selected entry
# keybind: Vyom/smriti leader:normal | Space y y | Copy the selected entry and stay open
# keybind: Vyom/smriti leader:normal | Space y p | Copy the selected entry's text, trimmed
# keybind: Vyom/smriti leader:normal | Space m p | Pin or unpin the selected entry
# keybind: Vyom/smriti leader:normal | Space d d | Delete the selected entry (asks first)
# keybind: Vyom/smriti leader:normal | Space d a | Clear the whole history; pins stay (asks first)
# keybind: Vyom/smriti leader:normal | Space o b | Open the selected link in the browser
# keybind: Vyom/smriti leader:normal | Space o e | Open the selected entry in $EDITOR
# END KEYBINDS

PINS = "smriti-pins"
TIMES = "smriti-times"
IMG = re.compile(r"^\[\[ binary data ([\d.]+ \w+) (\w+) (\d+)x(\d+) \]\]$")
CMD = re.compile(r"^(sudo |git |docker |npm |pnpm |yarn |cd |ls |cat |curl |ssh |pacman |systemctl |make |python3? |pip |"
                 r"kubectl |gh |cargo |go |rg |grep |find |sed |awk |tar |rsync |journalctl |kosha |vyom )")
CODE = re.compile(r"^\s*<[a-zA-Z!?]|[{};]\s*$|=>|\bfunction\b|\bdef |\bconst |\blet |\bimport |\bclass |"
                  r"\breturn\b|\bfn |\bfunc |</?\w+[^>]*>", re.M)
KINDS = {  # kind: (icon, color, label)
    "link": ("\U000f0337", "blue", "Link"),
    "image": ("\U000f02e9", "mauve", "Image"),
    "code": ("\U000f0169", "green", "Code"),
    "command": ("", "peach", "Command"),
    "email": ("\U000f01ee", "pink", "Email"),
    "text": ("\U000f0219", "teal", "Text"),
}
TABS = [("all", "All"), ("text", "Text"), ("image", "Images"), ("link", "Links"), ("code", "Code")]
GROUPS = ("Just now", "Today", "Yesterday", "Older")
THUMB_W, THUMB_H = 52, 36


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


def language(text):
    """A guess at code's language, or ""."""
    rules = [("Python", r"^\s*(def |class \w+.*:|import \w|from \w+ import)|\bself\.|:\s*$"),
             ("TypeScript", r":\s*(string|number|boolean)\b|\binterface \w+"),
             ("JavaScript", r"\b(const|let|var) \w+ =|=>|\bfunction\b|console\.|\bdocument\."),
             ("Rust", r"\bfn \w+\(|\blet mut\b|::\w+|\bimpl\b"),
             ("Go", r"\bfunc \w*\(|:= |\bpackage \w+"),
             ("HTML", r"^\s*<(!doctype|html|div|span|p|a|head|body)\b"),
             ("CSS", r"^[.#\w-][^{]*\{[^}]*:[^}]*;"),
             ("JSON", r"^\s*[\[{]\s*\"\w+\"\s*:"),
             ("Shell", r"^\s*(\$ |#!/bin/(ba)?sh|export \w+=|if \[)")]
    for name, rx in rules:
        if re.search(rx, text, re.M | re.I):
            return name
    return ""


def site_of(url):
    host = re.sub(r"^\w+://", "", url.strip()).split("/")[0].split("@")[-1].split(":")[0]
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) > 2 and not host.replace(".", "").isdigit() else host


def decode(line):
    try:
        return subprocess.run(["cliphist", "decode"], input=line.encode(), capture_output=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return b""


def age(t, now=None):
    """'now', '4 min', '11:20', 'Yesterday', 'Tue', '3 Nov'."""
    if not t:
        return ""
    now = now or time.time()
    d = now - t
    if d < 60:
        return "now"
    if d < 3600:
        return f"{int(d // 60)} min"
    a = datetime.datetime.fromtimestamp(t)
    days = (datetime.date.fromtimestamp(now) - a.date()).days
    if days == 0:
        return a.strftime("%H:%M")
    if days == 1:
        return "Yesterday"
    if days < 7:
        return a.strftime("%a")
    return f"{a.day} {a.strftime('%b')}"


def age_long(t):
    if not t:
        return "a while ago"
    a = age(t)
    return a + " ago" if a.endswith("min") else "just now" if a == "now" else a


def group_of(t, now):
    if not t:
        return "Older"
    if now - t < 600:
        return "Just now"
    days = (datetime.date.fromtimestamp(now) - datetime.date.fromtimestamp(t)).days
    return "Today" if days <= 0 else "Yesterday" if days == 1 else "Older"


# ---------------------------------------------------------------- colours
PALETTE = {"mauve": "#cba6f7", "green": "#a6e3a1", "peach": "#fab387", "blue": "#89b4fa", "overlay1": "#7f849c",
           "yellow": "#f9e2af", "teal": "#94e2d5", "sky": "#89dceb"}


def load_palette():
    """The theme's colours (Pango can't read CSS): the last @define-color of
    each in Vyom's stylesheets, as the theme loads last."""
    import vyom
    paths = [os.path.join(os.path.dirname(vyom.__file__), "style.css"),
             os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "vyom", "style.css")]
    try:
        from vyom import config
        extra = config.load().get("vyom", {}).get("css", [])
        paths += [os.path.expanduser(str(p)) for p in ([extra] if isinstance(extra, str) else extra)]
    except Exception:  # noqa: BLE001 -- the defaults are fine
        pass
    text = ""
    for p in paths:
        try:
            text += open(p).read() + "\n"
        except OSError:
            pass
    for name in PALETTE:
        found = re.findall(rf"@define-color\s+{name}\s+(#[0-9a-fA-F]{{6}})\s*;", text)
        if found:
            PALETTE[name] = found[-1]


KEYWORDS = set("""
and as async await break case catch class const continue def default del do elif else enum except export extends
false final finally fn for from func function go if impl import in interface is lambda let match mut new nil none
not null or package pass pub raise return self static struct super switch this throw true try type typeof use var
void while with yield None True False
""".split())
TOKEN = re.compile(r"(?P<comment>#[^\n]*|//[^\n]*|/\*.*?\*/)|(?P<string>\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'|`[^`]*`)"
                   r"|(?P<number>\b\d+(?:\.\d+)?\b)|(?P<word>[A-Za-z_]\w*)(?P<call>\s*\()?", re.S)


def highlight(code, lang=""):
    """Code as Pango markup: keywords mauve, strings green, numbers peach,
    calls blue, comments dim. Light on purpose: a preview, not an editor."""
    out, pos = [], 0
    esc = GLib.markup_escape_text
    hash_comments = lang in ("Python", "Shell", "")
    for m in TOKEN.finditer(code):
        out.append(esc(code[pos:m.start()]))
        pos = m.end()
        kind = m.lastgroup if m.lastgroup != "call" else "word"
        text = m.group(0)
        if m.group("comment") is not None:
            if text.startswith("#") and not hash_comments:
                out.append(esc(text))
                continue
            out.append(f"<span foreground='{PALETTE['overlay1']}' style='italic'>{esc(text)}</span>")
        elif kind == "string":
            out.append(f"<span foreground='{PALETTE['green']}'>{esc(text)}</span>")
        elif kind == "number":
            out.append(f"<span foreground='{PALETTE['peach']}'>{esc(text)}</span>")
        else:
            word = m.group("word")
            rest = text[len(word):]
            if word in KEYWORDS:
                out.append(f"<span foreground='{PALETTE['mauve']}'>{esc(word)}</span>{esc(rest)}")
            elif m.group("call"):
                out.append(f"<span foreground='{PALETTE['blue']}'>{esc(word)}</span>{esc(rest)}")
            else:
                out.append(esc(text))
    out.append(esc(code[pos:]))
    return "".join(out)


# ---------------------------------------------------------------- thumbnails
def round_thumb(src, dst):
    """A cropped, round-cornered PNG thumbnail of an image file (any thread)."""
    pb = GdkPixbuf.Pixbuf.new_from_file(src)
    w, h = pb.get_width(), pb.get_height()
    scale = max(THUMB_W / w, THUMB_H / h)
    sw, sh = max(THUMB_W, round(w * scale)), max(THUMB_H, round(h * scale))
    pb = pb.scale_simple(sw, sh, GdkPixbuf.InterpType.BILINEAR)
    pb = pb.new_subpixbuf((sw - THUMB_W) // 2, (sh - THUMB_H) // 2, THUMB_W, THUMB_H).copy()
    if not pb.get_has_alpha():
        pb = pb.add_alpha(False, 0, 0, 0)
    rs, n = pb.get_rowstride(), pb.get_n_channels()
    px = bytearray(pb.get_pixels())
    r = 9
    for cy in range(r):
        for cx in range(r):
            dx, dy = r - cx - 0.5, r - cy - 0.5
            cover = max(0.0, min(1.0, r - (dx * dx + dy * dy) ** 0.5 + 0.5))
            if cover >= 1:
                continue
            for x, y in ((cx, cy), (THUMB_W - 1 - cx, cy), (cx, THUMB_H - 1 - cy), (THUMB_W - 1 - cx, THUMB_H - 1 - cy)):
                o = y * rs + x * n + 3
                px[o] = int(px[o] * cover)
    out = GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(bytes(px)), GdkPixbuf.Colorspace.RGB, True, 8,
                                          THUMB_W, THUMB_H, rs)
    out.savev(dst, "png", [], [])


class Plugin(Base):
    name, title, icon, color = "smriti", "Clipboard", "\U000f014c", "teal"
    placeholder = "Search the clipboard…"
    preview = True
    preview_width = 340
    hints = [Hint("Enter", "copy"), Hint("p", "paste"), Hint("m", "pin"), Hint("d d", "delete")]
    insert_hints = [Hint("Enter", "copy"), Hint("Ctrl+Enter", "paste"), Hint("Esc", "normal mode")]
    modal = True                 # Vyom's vim keys (ADR 0008); smriti/vim.py
    start_mode = "insert"        # search-first
    key_groups = vim.GROUPS
    empty_text = "The clipboard history is empty"
    tabs = TABS              # Ctrl+H/L, Ctrl+1..5 (Vyom)

    def __init__(self, vyom, conf):
        super().__init__(vyom, conf)
        self.tab = "all"
        self.times_lock = threading.Lock()
        self.watcher = None
        load_palette()
        if self.conf.get("track_times", True):
            self.watch_clipboard()

    # ------------------------------------------------------------ times
    def watch_clipboard(self):
        """`wl-paste --watch echo`: a line per copy. Started on the main
        thread (its parent-death signal follows the thread that made it),
        so it ends with Vyom."""
        if not shutil.which("wl-paste") or not os.environ.get("WAYLAND_DISPLAY"):
            return
        try:
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
        except OSError:
            libc = None

        def die_with_vyom():
            if libc is not None:
                libc.prctl(1, signal.SIGTERM)   # PR_SET_PDEATHSIG
        try:
            self.watcher = subprocess.Popen(["wl-paste", "--watch", "echo"], stdout=subprocess.PIPE,
                                            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                            preexec_fn=die_with_vyom)
        except OSError:
            return
        GLib.io_add_watch(self.watcher.stdout.fileno(), GLib.PRIORITY_DEFAULT,
                          GLib.IOCondition.IN | GLib.IOCondition.HUP | GLib.IOCondition.ERR, self.copied)

    def copied(self, fd, cond):
        try:
            data = os.read(fd, 4096)
        except OSError:
            data = b""
        if not data or cond & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
            return False
        t = time.time()
        # cliphist stores it a moment later (its own wl-paste --watch)
        GLib.timeout_add(800, lambda: (threading.Thread(target=self.note_newest, args=(t,), daemon=True).start(), False)[1])
        return True

    def note_newest(self, t):
        try:
            p = subprocess.Popen(["cliphist", "list"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            line = p.stdout.readline().decode("utf-8", "replace")
            p.kill()
            p.wait()
        except OSError:
            return
        cid = line.split("\t", 1)[0]
        if cid.isdigit():
            with self.times_lock:
                st = util.load_state(TIMES, {})
                ids = st.setdefault("ids", {})
                if cid not in ids:
                    ids[cid] = t
                    st.setdefault("baseline", int(cid) - 1)
                    util.save_state(TIMES, st)

    def stamp(self, ids):
        """{id: time} for these cliphist ids, noting new ones."""
        with self.times_lock:
            st = util.load_state(TIMES, {})
            known = st.get("ids") or {}
            first = "baseline" not in st
            baseline = st.get("baseline", max((int(i) for i in ids), default=0))
            now, changed, out = time.time(), first, {}
            for i in ids:
                if i not in known:
                    known[i] = 0 if int(i) <= baseline else now
                    changed = True
                out[i] = known[i]
            if changed or len(known) > len(ids) + 100:
                keep = set(ids)
                util.save_state(TIMES, {"baseline": baseline, "ids": {k: v for k, v in known.items() if k in keep}})
            return out

    # ------------------------------------------------------------ search
    def search(self, q):
        code, out = util.run(["cliphist", "list"], timeout=5)
        entries = []
        for line in out.splitlines() if code == 0 else []:
            if "\t" not in line:
                continue
            cid, prev = line.split("\t", 1)
            if cid.isdigit():
                entries.append((line, cid, prev, kind_of(prev)))
        times = self.stamp([e[1] for e in entries])
        now = time.time()
        pins = util.load_state(PINS, {"items": []})["items"]
        pinned = {p["text"] for p in pins}
        rows = []
        if pins and not q:
            got = [p for p in pins if self.tab == "all" or self.in_tab(kind_of(p["text"]))]
            if got:
                rows.append(Section("Pinned", len(got), "m unpins"))
                rows += [self.pin_row(p) for p in got]
        groups, n, thumbs = {}, 0, 0
        for line, cid, prev, kind in entries:
            if not self.in_tab(kind):
                continue
            if q and util.fuzzy(q, prev) is None:
                continue
            thumb = ""
            if kind == "image" and thumbs < 40:
                thumbs += 1
                thumb = self.thumbnail(line, cid)
            row = self.row(line, cid, prev, kind, times.get(cid, 0), now, thumb, prev.strip() in pinned)
            groups.setdefault(group_of(times.get(cid, 0), now), []).append(row)
            n += 1
            if n >= 300:
                break
        for g in GROUPS:
            if g in groups:
                rows.append(Section(g, len(groups[g])))
                rows += groups[g]
        return rows

    def in_tab(self, kind):
        return self.tab == "all" or kind == self.tab or (self.tab == "text" and kind in ("email", "command"))

    def row(self, line, cid, prev, kind, t, now, thumb, pinned):
        icon, color, label = KINDS[kind]
        text = prev.strip().replace("\n", " ")[:200]
        esc = GLib.markup_escape_text
        m = IMG.match(prev.strip())
        if m:
            title = esc(f"Image {m.group(3)} × {m.group(4)}")
            sub = f"Image · {m.group(2).upper()} · {m.group(1)}"
        elif kind == "link":
            title = esc(re.sub(r"^\w+://", "", text).rstrip("/"))
            sub = f"Link · {site_of(text)}"
        elif kind in ("code", "command"):
            title = f"<span font_family='JetBrainsMono Nerd Font' size='94%'>{esc(text)}</span>"
            lang = language(prev) if kind == "code" else ""
            sub = " · ".join(x for x in (label, lang) if x)
        else:
            title = esc(text)
            words = len(prev.split())
            sub = f"{label} · {words} word{'s' if words != 1 else ''}" + ("…" if len(prev) >= 95 else "")
        return Row(title, esc(sub), icon=thumb or icon, color=color, meta=age(t, now), markup=True,
                   chips=[("Pinned", "yellow")] if pinned else None,
                   data={"line": line, "id": cid, "kind": kind, "preview": prev, "t": t})

    def pin_row(self, p):
        kind = kind_of(p["text"])
        icon, color, label = KINDS[kind]
        first = (p["text"].splitlines() or [""])[0][:200]
        esc = GLib.markup_escape_text
        title = f"<span font_family='JetBrainsMono Nerd Font' size='94%'>{esc(first)}</span>" \
            if kind in ("code", "command") else esc(first)
        return Row(title, label, icon=icon, color=color, markup=True, data={"pin": p, "kind": kind})

    # ------------------------------------------------------------ images
    def cache_dir(self):
        d = os.path.join(util.CACHE, "smriti")
        os.makedirs(d, exist_ok=True)
        return d

    def image_path(self, cid):
        return os.path.join(self.cache_dir(), f"{cid}.img")

    def thumbnail(self, line, cid):
        """A thumbnail file for the list (made once, in the search thread)."""
        thumb = os.path.join(self.cache_dir(), f"{cid}.thumb.png")
        if os.path.exists(thumb):
            return thumb
        try:
            if not os.path.exists(self.image_path(cid)):
                data = decode(line)
                if not data:
                    return ""
                with open(self.image_path(cid), "wb") as f:
                    f.write(data)
            round_thumb(self.image_path(cid), thumb)
            return thumb
        except (GLib.Error, OSError, ValueError, ZeroDivisionError):
            return ""

    # ------------------------------------------------------------ preview
    def build_preview(self, row):
        d = row.data
        kind = d["kind"]
        icon, color, label = KINDS[kind]
        if "pin" in d:
            text = d["pin"]["text"]
            head = ui.hbox(ui.chip(label, color, icon), ui.chip("Pinned", "yellow", "\U000f0403"), spacing=8)
            parts = [head, self.text_view(text, kind), ui.meta(self.size_text(text))]
            parts.append(self.button_rows([("Copy", lambda: (util.copy(text), self.close()), "primary", "", "Enter"),
                                           ("Paste", lambda: self.paste_text(text), "", "", "Ctrl+Enter"),
                                           ("Unpin", lambda: self.unpin(text), "", "\U000f0403", "m")]))
            return ui.vbox(*parts, spacing=10)
        parts = [ui.hbox(ui.chip(label, color, icon), ui.meta(f"copied {age_long(d['t'])}" if d["t"] else "copied a while ago"), spacing=8)]
        text = ""
        if kind == "image":
            path = self.image_path(d["id"])
            if os.path.exists(path):
                parts.append(ui.picture(path, 200))
            else:
                parts.append(ui.meta("loading…"))
                self.background(lambda: self.thumbnail(d["line"], d["id"]), lambda _r: self.panel.update_preview_soon())
            m = IMG.match(d["preview"].strip())
            if m:
                parts.append(ui.kv([("Size", f"{m.group(3)} × {m.group(4)}"), ("Format", m.group(2).upper()),
                                    ("Bytes", m.group(1))]))
        else:
            text = d.get("full") or d["preview"]
            if not d.get("full") and (len(text) >= 90 or kind == "code"):
                # cliphist's preview is cut and flattened: get the whole thing
                full = decode(d["line"]).decode("utf-8", "replace")
                d["full"] = text = full or text
            if kind == "link":
                parts.append(ui.title(site_of(text)))
            elif kind == "code" and language(text):
                parts[0].append(ui.chip(language(text), "gray"))
            parts.append(self.text_view(text, kind))
            parts.append(ui.meta(self.size_text(text)))
        pinned = text and any(p["text"] == text for p in util.load_state(PINS, {"items": []})["items"])
        specs = [("Copy", lambda: self.copy_entry(d), "primary", "\U000f018f", "Enter"),
                 ("Paste", lambda: self.copy_entry(d, paste=True), "", "\U000f0192", "Ctrl+Enter")]
        if kind != "image":   # a pin keeps text
            specs.append(("Unpin" if pinned else "Pin", lambda: self.unpin(text) if pinned else self.pin(d), "",
                          "\U000f0403", "m"))
        specs.append(("Delete", lambda: self.ask_delete(d), "danger", "\U000f01b4", "d d"))
        parts.append(self.button_rows(specs))
        return ui.vbox(*parts, spacing=10)

    def button_rows(self, specs):
        """Buttons two to a row (a narrow preview)."""
        box = ui.vbox(spacing=8)
        for i in range(0, len(specs), 2):
            row = Gtk.Box(spacing=8, homogeneous=True)
            for s in specs[i:i + 2]:
                row.append(ui.button(*s))
            box.append(row)
        return box

    def size_text(self, text):
        lines = text.count("\n") + 1
        return f"{len(text)} characters · {lines} line{'s' if lines != 1 else ''}"

    def text_view(self, text, kind):
        shown = text[:3000] + ("…" if len(text) > 3000 else "")
        w = Gtk.Label(xalign=0, wrap=True, wrap_mode=Pango.WrapMode.CHAR, selectable=False)
        w.add_css_class("p-mono")
        if kind == "code":
            w.set_markup(highlight(shown, language(text)))
        else:
            w.set_label(shown)
        if kind == "link":
            w.add_css_class("t-blue")
        return w

    # ------------------------------------------------------------ actions
    def copy_entry(self, d, paste=False):
        data = decode(d["line"])
        if not data:
            return
        subprocess.run(["wl-copy"], input=data, timeout=5)
        self.close()
        if paste:
            self.paste_after()

    def paste_text(self, text):
        util.copy(text)
        self.close()
        self.paste_after()

    def paste_after(self):
        if util.have("wtype"):
            subprocess.Popen(["sh", "-c", "sleep 0.15; wtype -M ctrl -k v -m ctrl"])

    def pin(self, d):
        text = d.get("full") or (decode(d["line"]).decode("utf-8", "replace") if d.get("kind") != "image" else "")
        if not text:
            self.set_status("images can't be pinned")
            return
        pins = util.load_state(PINS, {"items": []})
        if not any(p["text"] == text for p in pins["items"]):
            pins["items"].insert(0, {"text": text})
            util.save_state(PINS, {"items": pins["items"][:30]})
        self.set_status("pinned")
        self.panel.refresh_now(keep_selection=True)

    def unpin(self, text):
        pins = util.load_state(PINS, {"items": []})
        util.save_state(PINS, {"items": [p for p in pins["items"] if p["text"] != text]})
        self.set_status("unpinned")
        self.panel.refresh_now(keep_selection=True)

    def ask_delete(self, d):
        """Delete can't be undone: it asks first (y deletes)."""
        what = KINDS[d["kind"]][2].lower()
        # Which one, in the question: y must never delete an entry you didn't mean.
        snip = (d.get("preview") or "").strip().replace("\n", " ")
        snip = f" ({snip[:40]}{'…' if len(snip) > 40 else ''})" if snip else ""
        self.confirm(f"Delete this {what}{snip} from the history for good?", lambda: self.delete(d))

    def delete(self, d):
        subprocess.run(["cliphist", "delete"], input=d["line"].encode(), timeout=5)
        for f in (f"{d['id']}.img", f"{d['id']}.thumb.png"):
            try:
                os.unlink(os.path.join(self.cache_dir(), f))
            except OSError:
                pass
        self.set_status("deleted")
        self.refresh()

    def activate(self, row, mods):
        d = row.data
        if "pin" in d:
            if "ctrl" in mods:
                self.paste_text(d["pin"]["text"])
                return False
            util.copy(d["pin"]["text"])
            return True
        self.copy_entry(d, paste="ctrl" in mods)
        return False

    # ================================================================ keys
    # The modes, counts and sequences are Vyom's; smriti/vim.py is its keys.
    def keys(self, tab):
        return vim.keys(tab)

    def key(self, name, row, mods):
        # Ctrl+P in both modes (a chord: it never types)
        if name == "p" and mods == {"ctrl"} and row is not None:
            self.toggle_pin(row)
            return True
        return False

    def selected(self):
        return self.panel.selected_row() if self.panel else None

    def entry_text(self, d):
        if "pin" in d:
            return d["pin"]["text"]
        if d.get("kind") == "image":
            return ""
        return d.get("full") or decode(d["line"]).decode("utf-8", "replace")

    def toggle_pin(self, row):
        if "pin" in row.data:
            self.unpin(row.data["pin"]["text"])
            return
        text = row.data.get("full") or ""
        pinned = text and any(p["text"] == text for p in util.load_state(PINS, {"items": []})["items"])
        self.unpin(text) if pinned else self.pin(row.data)

    def v_pin(self, _n, _a):
        row = self.selected()
        if row is not None:
            self.toggle_pin(row)

    def v_paste(self, _n, _a):
        row = self.selected()
        if row is not None:
            self.activate(row, {"ctrl"})

    def v_copy(self, _n, arg):
        row = self.selected()
        if row is None:
            return
        d = row.data
        if arg == "plain" or "pin" in d:
            text = self.entry_text(d)
            if not text:
                self.set_status("an image has no text to copy", kind="bad")
                return
            util.copy(text.strip() if arg == "plain" else text)
        else:
            data = decode(d["line"])
            if data:
                subprocess.run(["wl-copy"], input=data, timeout=5)
        self.set_status("copied", kind="ok")

    def v_delete(self, _n, _a):
        row = self.selected()
        if row is None:
            return
        if "pin" in row.data:
            self.unpin(row.data["pin"]["text"])
        else:
            self.ask_delete(row.data)

    def v_wipe(self, _n, _a):
        def wipe():
            subprocess.run(["cliphist", "wipe"], timeout=10)
            self.set_status("cleared the history (pins stay)", kind="ok")
            self.refresh()
        self.confirm("Clear the whole clipboard history? Pins stay. It can't be undone.", wipe)

    def v_browser(self, _n, _a):
        row = self.selected()
        text = self.entry_text(row.data).strip() if row is not None else ""
        if row is None or row.data.get("kind") != "link" or not text:
            self.set_status("that isn't a link", kind="bad")
            return
        util.spawn(["xdg-open", text])
        self.close()

    def v_editor(self, _n, _a):
        row = self.selected()
        text = self.entry_text(row.data) if row is not None else ""
        if not text:
            self.set_status("an image can't open in an editor", kind="bad")
            return
        import tempfile
        fd, path = tempfile.mkstemp(prefix="smriti-", suffix=".txt")
        with os.fdopen(fd, "w") as f:
            f.write(text)
        term = self.conf.get("terminal") or os.environ.get("TERMINAL") or \
            next((t for t in ("kitty", "foot", "alacritty", "wezterm") if shutil.which(t)), "xterm")
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "nano"
        util.spawn([term, "-e", editor, path])
        self.close()
