---
name: ksp-play
description: Help the player while they play their KSP career — planning burns, transfers, captures, rendezvous or parking orbits, relay networks and comms, contracts, deployed science, kerbal XP, alarms, or diagnosing "why isn't X working". Use for any question about the game state or what to do next, rather than for changing the repo's code.
---

# KSP gameplay assistant

The player is in the game right now, often with the dashboard on a second monitor. Be fast, concrete and numerically right.

## Player setup

- Stock KSP 1.12.5 career + Breaking Ground (Serenity). MechJeb and KER installed.
- Stock CommNet, **Extra Ground Stations on**, Tracking Station L3: **DSN 250 G**. Kerbin needs no relays.
- `requireSignalForControl = False`. Still treat any burn without a link as unsafe.
- Network design and ring deployment rules: `docs/DSN_CheatSheet.md`.

## Start of every session

1. Read `notes/campaign.md` (roadmap + pending operations).
2. Check freshness: compare `data/digest.json` `header.mtime` (save written) and `generated_at`. If stale, or no `--serve` is running, run `python3 tools/ksp_digest.py`.
3. Read `data/digest.md` for the overview and `data/digest.json` for exact numbers.
4. For anything the digest lacks, grep the **live save, read-only** (path from `find_live_save()` in `tools/ksp_digest.py`):
   - `DeployedScience`: per-experiment TotalScienceGenerated / ScienceLimit, power, cluster
   - `CommNetParams`: occlusion multipliers, signal rules
   - contract `PARAM` blocks: e.g. sciencePercentage, scienceCollected
   - `AlarmClockScenario`, per-vessel `FLIGHTPLAN`, `TARGET`

## Doing the maths

- `import ksp_digest as k` (add `tools/` to `sys.path`). Reuse:
  - `state_vector`, `elements_from_state`, `orbit_info`, `kerbin_relative`
  - `BODIES`, `KERBIN_ORBIT`, `planets()`, `ksp_date`, `ksp_dur`
- Throwaway scripts go in `scratch/`. Never edit `tools/` during play.
- **Patched conics:** find the SOI entry by stepping the heliocentric orbit against the body's position. Convert to the body frame, then propagate with RK4 inside the SOI and apply nodes as impulses.
- **Simulate, don't eyeball:** check the claim the player makes ("I'll be 400 Mm away after half an orbit") before agreeing.
- Long burns: alarm `eventOffset` ≈ half the burn time. Check conditions over the whole burn window, not only at the node.
- Give instructions the player can act on directly:
  - game date (`Y# D# hh:mm`) and time from now
  - Δv as prograde/normal/radial in m/s
  - the number to trim to (period in seconds, or Ap/Pe as **altitude**)
  - what the dashboard should show afterwards
  - use tables for options

## Lessons from this campaign

- **Parking next to a planet:** match its **period**, not its velocity. "Kill target velocity" at a distance leaves an eccentric, drifting orbit, because the two craft move in slightly different directions.
- **The closest-approach readout is unreliable** for nearly co-orbital craft (it showed years and Gm). Use the simulation and the dashboard instead.
- **Alarm clock entry:** a relative "time from now" is easily typed as an absolute date. Check every new alarm in `digest.alarms`.
- **Maneuver nodes** can't easily be placed more than about one orbit out. Use an alarm and place the node later.
- **Comms during captures:**
  - A C-16 (500 k) reaches a vessel with 3× RA-15 (≈34 G combined) at about 131 Mm.
  - Check line of sight with the occlusion radius (0.75 × R for bodies with atmosphere, 0.9 × R in vacuum).
  - Capture the relay carrier **high and elliptical** first, so it isn't behind the planet while another craft brakes. Then lower it into the deployment orbit at no extra total cost.
- **Ring deployment:** carrier Ap = ring altitude, period ⅔ of the ring period; release one relay per Ap pass. Each relay circularizes, and all periods are matched to 0.1 s.
- **Breaking Ground seismometer:** only impacts generate science (≥3 kJ; Mun reference energy 7.82e8 J, scaling with ½mv²).
  - Crash heavy stages at full speed near the station.
  - Keep the impactor as the active vessel.
- **Kerbal XP:** levels only count on recovery at Kerbin, or as the game awards them. The digest's XP is an estimate.

## End of session: update `notes/campaign.md`

- **Rewrite, don't append.** Delete finished or obsolete items. Hard cap **400 words** (check with `wc -w`).
- Sections:
  - **Roadmap** (3–6 goals)
  - **Next up** (operations with date, craft, numbers)
  - **Contracts plan** (active ones needing action)
  - **Open decisions**
- No history or narrative. The save file and git hold the past.
