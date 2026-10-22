---
name: ksp-dev
description: Develop, fix or extend this repo's KSP tooling — tools/ksp_digest.py (save parser, digest.md/json/js, --watch/--serve) and web/dashboard.html (the tracking-station dashboard). Use whenever the request is to change code, add a feature, change the digest format, or debug the script or the dashboard, rather than to get help with the game itself.
---

# KSP tooling: development

You are improving the tools, not playing the game. Read `CLAUDE.md` first if you haven't.

## Architecture

**`tools/ksp_digest.py`** (stdlib only, ~920 lines), read top to bottom:

| Area | Functions | Notes |
|---|---|---|
| Constants | `BODIES`, `BODY_ORDER`, `KERBIN_ORBIT`, `XP_*`, `ANTENNAS`, `ENGINES`, `DENSITY`, `PLANET_ORBITS` | stock values; part names without `.v2` suffix |
| Parser | `Node`, `parse` | ConfigNode tree; repeated keys preserved (`getall`) |
| Format helpers | `ksp_date`, `ksp_dur`, `dist`, `f`, `base_part` | KSP calendar: 6 h day, 426 d year |
| Orbit maths | `orbit_info`, `position`, `state_vector`, `elements_from_state`, `kerbin_relative` | 2-body, parent-body frame; `elements_from_state` returns None for hyperbolic |
| Extractors | `career`, `kerbal_xp`/`level_for`/`kerbals`, `vessel`, `maneuvers`, `alarms`, `deployed_science`, `contracts`, `planets` | each returns plain dicts/lists |
| Output | `render` (markdown), `clean` (inf→null), `build` (writes `data/`), `serve`, `main` (watch loop) | `digest.js` written atomically via tmp + replace |
| Paths | `ROOT`, `DATA`, `SAVES`, `find_live_save()` | `$KSP_SAVE` / `$KSP_DIR`; never hard-code a user's save name |

**`web/dashboard.html`**: one file, inline CSS/JS, no libraries.
- Data: injects `<script src="../data/digest.js?t=…">` every 5 s; re-renders only when `header.generated_at` changes.
- Layout: top bar (with the most urgent alert as "next up" and career change since the previous save), vessel list (collapsible body groups), canvas map (system/body view, zoom/pan by mouse or touch, maneuver dashed orbits, `?` help overlay), side panel, tabs (Alerts with mute, Kerbals, Contracts, Network, Bodies). Below 1000 px wide everything stacks into one scrolling column.
- `alerts()` gives each alert a stable `key`; muted keys are dropped once their alert disappears, so a condition that clears and returns alerts again.
- JS orbit maths mirrors Python's (`rotator`, `trueAnomalyAt`, `posAt`, `orbitPath`, `helioPos`).
- UI state is kept in `localStorage` (`ksp-ts:*`); wrap access in try/catch.

## digest.json schema (top level)

- `header`: title, mode, version, ut, date, file, mtime (local-time string, display only), mtime_epoch (use for age maths), generated_at
- `career`: funds, science, reputation, techs_unlocked, facilities{name: 1–3}
- `kerbals[]`: name, trait, type, state, vessel, xp, level, xp_if_recovered_now, level_if_recovered_now, flights, best_by_body
- `vessels[]`: pid, name, type, situation, lat/lon/alt, crew, `orbit`{body, ref, SMA, ECC, INC, LAN, LPE, MNA, EPH, ap_alt, pe_alt, period_s}, resources{name:[cur,max]}, antennas, engines, `dv_stages[]`{stage, engines, dv_ms, mass_t} (vacuum, launch first), dv_total_ms, labs, lab_data, docking_ports, target, `maneuvers[]`{ut, date, time_until_s, prograde, normal, radial, total, after{orbit…, kerbin_relative_at_burn}}, `kerbin_relative` (Kerbol orbiters only), `asteroid`{size_class, tracked, lost_in_s} (SpaceObjects only)
- `contracts[]`: type, state, agent, title (ContractConfigurator only), target_body, funds_*, science, rep_*, deadline_ut, time_left_s, params[]
- `alarms[]`: title, type, description, vessel, vessel_pid, ut, date, time_until_s, triggered, maneuver_ut
- `deployed_science[]`: body, controller_pid, `experiments[]`{name, vessel_pid, enabled, generated, limit, transmitted, stored, no_comms, no_power}
- `planets[]`: idx, name, radius, GM, atm, parent, color, soi, orbit

**Rule:** any schema change updates `render()` and the dashboard in the same change. Keep `digest.md` compact (it is @-mentioned into chats; target <350 lines; it grows ~6 lines per vessel).

## KSP save facts (easy to get wrong)

- CRLF line endings; tab-indented ConfigNode format.
- Facility `lvl` is normalized 0 / 0.5 / 1, which is level 1 / 2 / 3.
- Maneuver `dV = radial, normal, prograde` (in that order) in the node's orbit frame.
- Kerbin: SMA 13,599,840,256 m, ECC 0, MNA 3.14 at epoch 0. Kerbol radius 261.6 Mm.
- The in-game Ap/Pe readout is **altitude above the surface**, not radius.
- Alarm `vesselId` is the vessel's `persistentId` (not `pid`).
- Contract `targetBody` is a body index in stock contracts but a body **name** in ContractConfigurator ones (`body_name()` handles both).
- Staging: PART `parent` is the index of its parent part (root: itself); `istg` is the KSP stage number. Fired decouplers keep `isDecoupled = True`; heat shields carry `ModuleDecouple` with `stagingEnabled = False`.
- Kerbals have no stored XP. It is estimated from `CAREER_LOG` with the `XP_*` table (unverified against the game).
- Maneuvers after an SOI change are not predicted (current limitation).
- A craft's `ORBIT` is in its current SOI's frame (`REF` = body index).
- Asteroids/comets (`SpaceObject`): `DISCOVERY` `state` 1 = untracked (presence only), `size` 0–8 = class A–I; an untracked one is lost at `lastObservedTime + lifetime`. Their PART `mass` (150) is a placeholder.
- `DeployedScience` scenario: SCIENCECLUSTER → MANNEDSCIENCEPARTS → MANNEDSCIENCEPART → EXPERIMENT. `VesselId` is the vessel `pid` with dashes; `ControlModulePartId` is a PART `persistentId`.

## Workflow

1. Edit. For bigger dashboard changes, work on a copy in `scratch/dashboard.html` (gitignored; `../data/digest.js` still resolves) and copy it to `web/` once verified, so a half-done page is never live.
2. Run `python3 tools/ksp_digest.py` (newest `saves/*.sfs`, else the live save; read-only). Check that the JSON is valid and `digest.md` reads well.
3. Preview the dashboard: start the `dashboard` config from `.claude/launch.json` (runs `--serve` on :8765) and open `/web/dashboard.html` in the browser pane.
   - If the player already runs `--serve` (port 8765 busy), use that server: it serves files from disk, so dashboard edits show on reload. Its watcher still runs the old Python until restarted and may overwrite `data/` mid-test: rerun the one-shot digest before checking.
   - Check the console for errors.
   - Check the layout at 1920×1080.
   - Click through a vessel, the map and every tab.
   - Under an emulated viewport, click by JS/refs, because coordinate clicks can be off.
4. Background processes: stop any watcher or server you start (`kill <pid>`). SIGINT does not reach background jobs, and orphaned watchers keep rewriting `data/`.
5. Before committing, `git status`, and confirm that no personal paths, saves or `data/` are staged. Commit with a clear message.

## Backlog (known gaps)

- **SOI-aware prediction:** SOI entry time, arrival periapsis, and the orbit after a capture node. The play-session prototype used SOI search plus RK4 inside the SOI.
- **CommNet link check:** per vessel and over burn windows, including occlusion (`occlusionMultiplierAtm` 0.75, `Vac` 0.9) and combined relay power `strongest × (sum/strongest)^0.75`.
- **Verify against the game:** the XP table (Astronaut Complex), asteroid class letters and signal-lost time (Tracking Station), and alarm field names (`type`, `vesselId`, `maneuverUT`; no real alarm has been parsed yet).
- **Δv fuel flow:** stages burn only the fuel in the parts they drop; no fuel lines/crossfeed rules, solid boosters (and Making History SRBs) not in `ENGINES`.
