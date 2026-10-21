# 3. Read cliphist's history rather than keeping our own

**Status:** Accepted  
**Date:** 2026-10-19

## Context

Clipboard history needs a watcher running all the time, storage and deletion. cliphist already does this well on Wayland and other tools read it.

## Decision

smriti is only the interface: it lists, previews, copies, pins and deletes through `cliphist`. Pins are kept by smriti in its own state file.

## Consequences

- No second clipboard daemon.
- smriti requires cliphist (and `wl-clipboard`) to be set up.
