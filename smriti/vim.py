"""smriti's vim keys, as data. The modes, counts, sequences, which-key strip,
help (?) and palette (Space Space) are Vyom's (vyom/keys.py, vyom/modal.py;
Vyom ADR 0008); this file is only what smriti adds. Space groups follow
Vayu's shared letters: t tabs (Vyom's), y copy, m mark (pin), d delete,
o open outside, u toggles.

An action "verb:arg" runs Plugin.v_<verb>(count, arg) in smriti/__init__.py,
or Vyom's own (activate, insert, moved...).
"""
from vyom.keys import Bind

B = Bind

GROUPS = {}

INSERT = [
    ("Enter", "Copy the selected entry"),
    ("Ctrl+Enter", "Paste the selected entry (copies it, then pastes into your window)"),
]

NORMAL = [
    B("<CR>", "activate", "Copy the selected entry and close"),
    B("p", "paste", "Paste the selected entry into your window"),
    B("yy", "copy", "Copy the selected entry and stay open"),
    B("m", "pin", "Pin or unpin the selected entry"),
    B("dd", "delete", "Delete the selected entry (a pinned one: unpin it; asks first)"),
    B("<Del>", "delete", "", hidden=True),
    B("<C-CR>", "paste", "", hidden=True),
]

BOTH = [("Ctrl+P", "Pin or unpin the selected entry")]

LEADER = [
    B(" yy", "copy", "Copy the selected entry and stay open"),
    B(" yp", "copy:plain", "Copy the selected entry's text, trimmed"),
    B(" mp", "pin", "Pin or unpin the selected entry"),
    B(" dd", "delete", "Delete the selected entry (asks first)"),
    B(" da", "wipe", "Clear the whole history; pins stay (asks first)"),
    B(" ob", "browser", "Open the selected link in the browser"),
    B(" oe", "editor", "Open the selected entry in $EDITOR"),
]


def keys(tab):
    return NORMAL + LEADER


SECTIONS = [
    ("smriti", "insert", "Insert mode (typing; smriti opens in it)", INSERT),
    ("smriti", "normal", "Normal mode", NORMAL),
    ("smriti", "any", "Both modes", BOTH),
    ("smriti leader", "normal", "Leader (Space)", LEADER),
]
