# Dacheng Whiteboard — Canonical Location

## Source of truth
- **Primary whiteboard root:** `./`
- **Current state JSON:** `./state_backups/current_state.json`
- **Daily snapshots:** `./state_backups/daily/`
- **Revisions:** `./state_backups/revisions/`

## Standard rule
If you update "the whiteboard", update the JSON state in this folder.

## Public repo note
This repository ships with sanitized sample data so it can be shared safely.
Replace the sample JSON with your own local state if you want to use it as a real daily board.

## Operator note
When there is any conflict, the JSON files in this folder win.
