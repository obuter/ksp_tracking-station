# KSP Tracking Station

Companion tooling for a stock **Kerbal Space Program 1.12.5** career: a script that condenses the huge `.sfs` save into a compact digest, and a live "tracking station" dashboard for a second monitor. Sessions in this folder are either **development** (improving the tools) or **gameplay** (helping the player while they play).

## Session mode: decide at the start of every session

| The user is… | Mode | Load skill |
|---|---|---|
| asking about the game: craft, orbits, burns, transfers, contracts, kerbals, comms, science, "what should I do next", "why isn't X working" | **play** | `ksp-play` |
| asking to change/fix/extend `tools/ksp_digest.py`, `web/dashboard.html`, the digest format, watch/serve | **dev** | `ksp-dev` |

- If the first message doesn't make it clear, ask in one line ("game help or tool work?").
- A play session that discovers a tool gap does **not** edit the tools. Note the gap and suggest a dev session (or add it to the backlog in the `ksp-dev` skill).

## Folder map

```
CLAUDE.md                  this file
README.md / LICENSE        public repo docs (MIT)
tools/ksp_digest.py        save parser → data/digest.{md,json,js}; --watch / --serve
web/dashboard.html         single-file dashboard, polls ../data/digest.js every 5 s
docs/DSN_CheatSheet.md     CommNet network design: antennas, ranges, relay rings, ring deployment
notes/campaign.md          living game plan, ≤400 words (gitignored, personal)
notes/campaign.template.md empty skeleton of the above (committed)
data/                      generated digest files (gitignored)
saves/                     optional .sfs snapshots (gitignored)
scratch/                   throwaway analysis scripts from play sessions (gitignored)
.claude/skills/            ksp-dev, ksp-play
.claude/launch.json        "dashboard" preview config (runs --serve on :8765)
```

## Commands (run from the repo root)

```bash
python3 tools/ksp_digest.py --serve        # watch the live save + serve http://localhost:8765/web/dashboard.html
python3 tools/ksp_digest.py                # one-shot: newest saves/*.sfs, else the live save
python3 tools/ksp_digest.py --save X.sfs   # a specific save
python3 tools/ksp_digest.py --all          # include debris, flags, asteroids, deployed science
```

The live save is found automatically: `$KSP_SAVE`, otherwise the most recently written `saves/*/persistent.sfs` under `$KSP_DIR` (default: the macOS Steam install).

## Hard rules

- **Never write into the KSP install or its saves folder.** Saves are read-only input.
- **Standard library only:** no pip packages in Python, no CDN/external libraries in the dashboard.
- **This repo is public:** never commit personal paths, emails, save files, or generated data. `.gitignore` covers `data/`, `saves/`, `scratch/`, `*.sfs`, `notes/campaign.md`.
- **`notes/campaign.md` is ≤400 words.** Rewrite it rather than append; delete finished items.
