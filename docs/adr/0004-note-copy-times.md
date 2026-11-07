# 4. Note when each entry was copied

**Status:** Accepted  
**Date:** 2026-11-07

## Context

The redesign groups the history by time (Just now, Today, Yesterday, Older), but cliphist stores only an id and the data: no times.

## Decision

While Vyom runs, smriti runs `wl-paste --watch echo` (started from the daemon's main thread with a parent-death signal, so it ends with Vyom). On each copy it waits a moment for cliphist to store it, reads cliphist's newest id and saves `id → time` in `~/.local/state/vyom/smriti-times.json`. An id it didn't see arrive gets the time it was first listed; ids from before smriti first ran get no time and go under Older. `track_times = false` turns the watcher off.

## Consequences

- Times are right for everything copied while Vyom runs; copies made while it wasn't get the time the panel next opened.
- One small extra process for the session, and one `cliphist list` per copy.
