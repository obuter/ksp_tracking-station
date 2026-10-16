# Stock CommNet Deep-Space Network — Build & Launch Cheat Sheet

**Stock Kerbol system · stock CommNet · Extra Ground Stations ENABLED · Tracking Station Level 3 (250 G DSN)**

**Topology in one line:** Kerbin is fully covered from the ground (extra ground stations), so **no Kerbin relay constellation is needed** — you just build a **3-relay ring at every body/moon** you operate on, to keep control on the far side and behind the body. Relay count scales with *bodies*, never *rovers*.

---

## 0. What CommNet Gives You (and what it doesn't)

- **Antennas are omnidirectional and link automatically.** Any two nodes that are in range and have line-of-sight connect — nothing to aim or configure.
- **Range = `√(Power_A × Power_B)`** between any two nodes (antenna powers, in the same units). Farther apart = weaker; past the computed range the link drops.
- **Relay vs Direct:** only **Relay** antennas can pass *other* craft's signals. **Direct** antennas talk only for their own craft. Every relay-ring satellite MUST use a relay antenna.
- **Occlusion:** a body blocks signal that passes through it (plus a thin shell above atmospheres). This is the whole reason for body rings — a lander on the far side has no direct LOS to Kerbin.
- **No connection = no probe control** (loss of control / "control lock"). A crewed pod or the difficulty setting can override, but assume probes need a live link.

---

## 1. Home Side — the Deep Space Network (ground)

- **Extra Ground Stations is on**, so multiple DSN sites ring Kerbin → **any craft with LOS to Kerbin links, regardless of which way Kerbin is facing.** Kerbin needs no relay satellites of its own.
- **DSN power = 250 G** (Tracking Station fully upgraded — assumed throughout this sheet). All ranges below are computed against this.

---

## 2. Antenna Reference — stock parts

| Antenna | Power | Type | Range to DSN | Notes |
|---|---|---|---|---|
| Internal (probe cores) | 5 k | Direct | 35 Mm | emergency only, near-Kerbin |
| **Communotron 16** | 500 k | Direct | 354 Mm | rover/lander uplink to a ring |
| Communotron 16-S | 500 k | Direct | 354 Mm | surface-mount version |
| **HG-5 High Gain** | 5 M | **Relay** | 1.12 Gm | Mun/Minmus rings, Jool moon rings |
| **Communotron DTS-M1** | 2 G | Direct | 22.4 Gm | mid-range craft antenna |
| **RA-2 Relay** | 2 G | **Relay** | 22.4 Gm | inner-planet rings |
| Communotron HG-55 | 15 G | Direct | 61.2 Gm | strong direct, out to Dres |
| **RA-15 Relay** | 15 G | **Relay** | 61.2 Gm | mid-system rings |
| **Communotron 88-88** | 100 G | Direct | 158 Gm | strongest **direct** — reaches DSN from anywhere in stock |
| **RA-100 Relay** | 100 G | **Relay** | 158 Gm | Jool/Eeloo rings, strongest relay |

**Combining:** same-type combinable antennas stack with diminishing returns (`strongest × (sum/strongest)^exponent`, exponent ≈ 0.75 for the big relays). Add a second identical antenna for range margin if a body sits near the edge.

### Range matrix — any antenna ↔ any antenna

`Range = √(Power_A × Power_B)`. Find the weaker end's row, the stronger end's column. When linking *through* a relay, that end counts only its **relay** antennas.

| ↓ / → | Internal 5 k | C-16 / 16-S 500 k | HG-5 5 M | DTS-M1 / RA-2 2 G | HG-55 / RA-15 15 G | 88-88 / RA-100 100 G | **DSN 250 G** |
|---|---|---|---|---|---|---|---|
| **Internal 5 k** | 5 km | 50 km | 158 km | 3.2 Mm | 8.7 Mm | 22 Mm | 35 Mm |
| **C-16 / 16-S 500 k** | | 500 km | 1.6 Mm | 32 Mm | 87 Mm | 224 Mm | 354 Mm |
| **HG-5 5 M** | | | 5 Mm | 100 Mm | 274 Mm | 707 Mm | 1.12 Gm |
| **DTS-M1 / RA-2 2 G** | | | | 2 Gm | 5.5 Gm | 14.1 Gm | 22.4 Gm |
| **HG-55 / RA-15 15 G** | | | | | 15 Gm | 38.7 Gm | 61.2 Gm |
| **88-88 / RA-100 100 G** | | | | | | 100 Gm | 158 Gm |

(1 Mm = 1,000 km · 1 Gm = 1,000,000 km)

---

## 3. Distances to Kerbin

Min = closest approach (same side of Kerbol). Max = opposite sides of Kerbol — **at max distance the Sun is on the sightline** (see §8 Solar conjunction). Moons add at most their orbit around the parent.

| Body | Min distance | Max distance | Smallest relay that covers max |
|---|---|---|---|
| Mun | 12.0 Mm | 12.0 Mm | HG-5 (1.12 Gm) |
| Minmus | 47.0 Mm | 47.0 Mm | HG-5 (1.12 Gm) |
| Moho | 7.3 Gm | 19.9 Gm | RA-2 (22.4 Gm) |
| Eve (+ Gilly) | 3.7 Gm | 23.6 Gm | RA-15 (61.2 Gm) — RA-2 covers all but near-conjunction |
| Duna (+ Ike) | 6.1 Gm | 35.4 Gm | RA-15 (61.2 Gm) |
| Dres | 21.3 Gm | 60.4 Gm | RA-15 (61.2 Gm) — thin margin, 2× RA-15 or RA-100 for safety |
| Jool (+ moons) | 51.5 Gm | 86.0 Gm | RA-100 (158 Gm) |
| Eeloo | 53.1 Gm | 127.2 Gm | RA-100 (158 Gm) |

---

## 4. Interplanetary craft — reaching DSN directly

A probe that only needs to talk to *Kerbin* (not relay for others) just needs a direct antenna strong enough at that distance (compare §2 range to §3 max distance):

| Antenna | Range to DSN | Good out to |
|---|---|---|
| Communotron 16 | ~0.35 Gm | near-Kerbin / Mun / Minmus |
| DTS-M1 | ~22 Gm | Moho; Eve except near conjunction |
| HG-55 | ~61 Gm | Eve, Duna, Dres |
| **Communotron 88-88** | ~158 Gm | **everything, incl. Eeloo** |

→ **Put an 88-88 on any deep-space probe** and it always reaches the DSN when it has LOS to Kerbin. Rings handle the LOS-blocked cases (far side, behind the body).

---

## 5. BODY RELAY RING — 3 relays @ 120° at every body/moon

Three relays evenly spaced above the body's radius **self-mesh** (each in range of its neighbours) and guarantee that a craft anywhere on/around the body reaches a ring member, which routes around to whichever member currently faces Kerbin. This is what prevents far-side control loss.

**Each ring sat = probe core + power + ONE relay antenna** (sized to reach Kerbin from that body — see table). The same relay antenna also handles the short ring-to-ring mesh, so one antenna does everything.

### Ring altitude + home-relay antenna

| Body | Radius | **Ring alt** | **Relay antenna** | | Body | Radius | **Ring alt** | **Relay antenna** |
|---|---|---|---|---|---|---|---|---|
| Mun | 200 km | 300 km | HG-5 | | **Jool hub** | 6,000 km | **8,000 km** | RA-100 |
| Minmus | 60 km | 100 km | HG-5 | | Laythe | 500 km | 700 km | HG-5 (→hub) |
| Moho | 250 km | 300 km | RA-2 | | Vall | 300 km | 450 km | HG-5 (→hub) |
| Eve | 700 km | 1,000 km | RA-15 | | Tylo | 600 km | 800 km | HG-5 (→hub) |
| Gilly | 13 km | 30 km | RA-15 | | Bop | 65 km | 150 km | HG-5 (→hub) |
| Duna | 320 km | 500 km | RA-15 | | Pol | 44 km | 80 km | HG-5 (→hub) |
| Ike | 130 km | 150 km | RA-15 | | Eeloo | 210 km | 250 km | RA-100 |
| Dres | 138 km | 150 km | RA-15 | | | | | |

**Altitude rule:** circular and **ring alt > body radius + 2 × atmosphere height** (Eve 90, Duna 50, Laythe 50, Jool 200 km). That puts the midpoint of the 120° chord between neighbours above the atmosphere, so the ring self-meshes. Higher = wider horizon = better far-side/pole coverage; the values above are comfortable minimums.

**Relay-antenna rule:** pick the smallest relay whose DSN range (§2) exceeds the body's max distance to Kerbin (§3).

### Jool system — one RA-100 hub ring + small HG-5 moon rings

Build a **hub ring around Jool** that carries all Jool→Kerbin traffic, so the moons only need to reach the hub — not Kerbin — and can run tiny antennas.

- **Jool hub ring:** 3 @ 120° at **8,000 km** — i.e. **inside all the moons, hugging Jool** (ring radius 14 Mm; satisfies the altitude rule for Jool's 6,000 km radius and 200 km atmosphere). Each sat = **RA-100** (reaches the DSN from Jool's ~86 Gm max; RA-100 range = 158 Gm). Placing it low keeps every moon link short; an outer hub only lengthens links with no occlusion benefit.
- **Each active moon** (Laythe/Vall/Tylo/Bop/Pol): its own 3 @ 120° ring at the table altitude, each sat = **HG-5** (relay). HG-5→RA-100 hub reaches ~707 Mm — covers even Pol (~210 Mm from Jool at apoapsis) with >3× margin. Rovers reach the moon ring on a Communotron 16.
- **Why it self-heals:** three hub members 120° apart always keep ≥1 on any moon's near side (so far-side-of-Jool moons still reach the hub) and ≥1 on the Kerbin-facing side (so the hub always reaches home). The ring also covers craft in Jool orbit/atmosphere.
- **Single point of failure:** all Jool traffic funnels through the hub. Add a 4th hub sat, or put one RA-100 on a single moon ring as a backup home link.

### Eeloo

Lone body, no moons → a single 3 @ 120° ring (RA-100, 250 km) is all it needs. RA-100 covers Eeloo even at max distance (~127 Gm < 158 Gm).

---

## 6. Deploying a ring — one carrier, three relays

Carry all three relays on one carrier. Put the carrier on a **resonant orbit with apoapsis = ring altitude and period = ⅔ of the ring period**, and release one relay at each apoapsis pass.

**How it works:** each released relay circularizes at apoapsis (ring period `T`). The carrier returns to apoapsis after `⅔ T`, by which time the previous relay has moved 240° — i.e. it sits 120° behind the release point. Three releases on three consecutive apoapsis passes → **0° / 120° / 240°**.

**Formula:** `r_ring = R + ring alt` · `r_Pe = 0.5263 × r_ring` · **carrier Pe altitude = 0.5263 × (R + ring alt) − R**

### Carrier orbit per body (Ap = ring alt)

| Body | Ring alt (= carrier Ap) | **Carrier Pe** | Ring period `T` | **Carrier period (⅔ T)** | Relay circularize Δv |
|---|---|---|---|---|---|
| Mun | 300 km | **63 km** | 2h 25m 03.9s | **1h 36m 42.6s** | 61 m/s |
| Minmus | 100 km | **24 km** | 2h 39m 29.5s | **1h 46m 19.7s** | 18 m/s |
| Moho | 300 km | **40 km** | 1h 44m 01.4s | **1h 09m 20.9s** | 94 m/s |
| Eve | 1,000 km | **195 km** | 1h 21m 11.9s | **54m 07.9s** | 372 m/s |
| Gilly | 30 km | **9.6 km** | 5h 24m 19.5s | **3h 36m 13.0s** | 2.4 m/s |
| Duna | 500 km | **112 km** | 2h 21m 38.8s | **1h 34m 25.8s** | 103 m/s |
| Ike | 150 km | **17 km** | 1h 53m 51.7s | **1h 15m 54.5s** | 44 m/s |
| Dres | 150 km | **14 km** | 1h 50m 25.3s | **1h 13m 36.9s** | 46 m/s |
| **Jool hub** | 8,000 km | **1,368 km** | 5h 26m 21.3s | **3h 37m 34.2s** | 762 m/s |
| Laythe | 700 km | **132 km** | 1h 38m 16.6s | **1h 05m 31.1s** | 217 m/s |
| Vall | 450 km | **95 km** | 2h 29m 19.5s | **1h 39m 33.0s** | 89 m/s |
| Tylo | 800 km | **137 km** | 1h 43m 12.1s | **1h 08m 48.1s** | 241 m/s |
| Bop | 150 km | **48 km** | 3h 29m 20.7s | **2h 19m 33.8s** | 18 m/s |
| Pol | 80 km | **21 km** | 2h 50m 12.5s | **1h 53m 28.4s** | 13 m/s |
| Eeloo | 250 km | **32 km** | 1h 59m 46.2s | **1h 19m 50.8s** | 68 m/s |

Every carrier Pe above clears the body's atmosphere and highest terrain. Times in Kerbin hours (6 h day).

### Procedure

1. **Arrive** and put the carrier in an equatorial orbit with **Ap = ring alt, Pe = table value**.
2. **Trim the period**, not the Pe: fine-tune with low thrust / RCS until the carrier period matches the table to within ~1 s. The period is what sets the spacing.
3. **At Ap: release relay #1.** It burns prograde (table Δv) to circularize at ring alt, then trims its own period to exactly `T`.
4. **Coast one carrier orbit. At Ap: release relay #2**, circularize, trim to `T`.
5. **Coast one more orbit. At Ap: release relay #3**, circularize, trim to `T`.
6. **Verify:** three relays ~120° apart, all with **identical periods** (match to ~0.1 s so the spacing never drifts), and each shows a link to its neighbours.

**Relay sats need their own small engine or RCS + fuel** for the circularize burn and trim. The carrier can then deorbit or move on to the next body.

**Fallback — two orbits between releases:** if a carrier Pe would ever be too low (bigger payload, different ring alt), use **period = ⅚ T** and release every **second** Ap pass (relay advances 600° = 240° per release gap → same 120° spacing). Pe factor becomes `0.7710 × r_ring` — much higher Pe, smaller circularize burn, one extra orbit per release.

---

## 7. Rovers / landers / local craft

- **Communotron 16** (direct) → links to the body ring overhead, which relays home. That's all a surface craft needs.
- Deep-space craft that will sit where Kerbin has LOS can skip the ring and carry an **88-88** to hit the DSN directly (§4).

---

## 8. Occlusion — why 3 @ 120°

- The frequent blocker is **the body itself** — a lander on the far side has no LOS to Kerbin.
- Three relays at 120°, above the body's radius, always leave **at least one member with LOS to Kerbin** and keep the ring self-meshed, so far-side traffic hops around the ring to the Kerbin-facing member.
- Two relays at 180° can't see each other (the body blocks the chord) and leave a rotating gap — use three.
- Tiny low-traffic moons (Gilly/Bop/Pol) can run **one** relay if you only need occasional coverage, accepting gaps.

### Solar conjunction (Sun between Kerbin and the target)

When Kerbol sits on the sightline it fully blocks the link (Kerbol radius ~261.6 Mm — a big, long occulter). A body relay ring can't help; the whole planet is behind the Sun. Two stages:

- **Early game — ride it out.** Conjunction happens once per synodic period and is temporary. Safe the probe, queue nothing critical, wait for the geometry to clear (this is what real missions do).
- **End game — heliocentric relay trio.** 3 relays in **identical circular solar orbits, 120° apart** (≈Kerbin's orbital radius, ~13.6 Gm), each **RA-100**. Same semi-major axis = same period, so the 120° spacing holds forever with no station-keeping. For any planet behind the Sun there's always a trio member off the Sun line with LOS to both it and Kerbin → **zero conjunction blackout, system-wide.** (A single offset heliocentric relay is a cheaper stopgap, but it drifts and only helps when it happens to be off-axis.)

---

## 9. Launch / build checklist

- [ ] **Deep-space probes:** carry a **Communotron 88-88** — reaches the 250 G DSN from anywhere in the system with LOS.
- [ ] **Body rings:** 3 relays @ 120°, circular at the table altitude, each with the table's relay antenna.
- [ ] **Carrier:** Ap = ring alt, Pe = table value, period trimmed to ⅔ T; release one relay per Ap pass.
- [ ] **Relays:** each has engine/RCS for its circularize Δv; all three periods matched to ~0.1 s. Confirm the three self-mesh and at least one shows a Kerbin link as the body rotates.
- [ ] **Rovers/landers:** Communotron 16 is enough to reach the ring.
- [ ] Before a far launch: is the craft's antenna range (§2) ≥ the target's max distance (§3)?

---

*Start with a 3-relay ring at Mun (300 km, HG-5). Add a ring per body you operate on, sized by the table. Kerbin needs nothing — the ground stations have it covered.*
