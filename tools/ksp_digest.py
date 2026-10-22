#!/usr/bin/env python3
"""Condense a KSP .sfs save into a compact digest (data/digest.md, .json, .js).

Usage (from the repo root):
    python3 tools/ksp_digest.py                 # newest *.sfs in saves/, else KSP's live save
    python3 tools/ksp_digest.py --save X.sfs    # specific save
    python3 tools/ksp_digest.py --all           # include debris, flags, asteroids, deployed science
    python3 tools/ksp_digest.py --watch        # regenerate whenever the live persistent.sfs changes
    python3 tools/ksp_digest.py --serve         # --watch + dashboard on http://localhost:8765/web/dashboard.html

Live save lookup: $KSP_SAVE (full path to a .sfs), else the most recently written
saves/*/persistent.sfs under $KSP_DIR (default: the macOS Steam install).
"""
import argparse
import datetime as dt
import json
import math
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
SAVES = ROOT / "saves"
DEFAULT_KSP_DIR = Path.home() / "Library/Application Support/Steam/steamapps/common/Kerbal Space Program"

# ---------------------------------------------------------------- constants

# idx: (name, radius m, GM m^3/s^2, atmosphere m, parent idx)
BODIES = {
    0: ("Kerbol", 261_600_000, 1.1723328e18, 600_000, None),
    1: ("Kerbin", 600_000, 3.5316e12, 70_000, 0),
    2: ("Mun", 200_000, 6.5138398e10, 0, 1),
    3: ("Minmus", 60_000, 1.7658e9, 0, 1),
    4: ("Moho", 250_000, 1.6860938e11, 0, 0),
    5: ("Eve", 700_000, 8.1717302e12, 90_000, 0),
    6: ("Duna", 320_000, 3.0136321e11, 50_000, 0),
    7: ("Ike", 130_000, 1.8568369e10, 0, 6),
    8: ("Jool", 6_000_000, 2.82528e14, 200_000, 0),
    9: ("Laythe", 500_000, 1.962e12, 50_000, 8),
    10: ("Vall", 300_000, 2.074815e11, 0, 8),
    11: ("Bop", 65_000, 2.4868349e9, 0, 8),
    12: ("Tylo", 600_000, 2.82528e12, 0, 8),
    13: ("Gilly", 13_000, 8.289e6, 0, 5),
    14: ("Pol", 44_000, 7.2170208e8, 0, 8),
    15: ("Dres", 138_000, 2.1484489e10, 0, 0),
    16: ("Eeloo", 210_000, 7.4410815e10, 0, 0),
}
BODY_ORDER = [0, 4, 5, 13, 1, 2, 3, 6, 7, 15, 8, 9, 10, 12, 11, 14, 16]
# idx: SMA, ECC, INC, LAN, LPE, MNA (rad, at epoch 0), SOI radius, map colour
PLANET_ORBITS = {
    1: (13_599_840_256, 0.0, 0.0, 0.0, 0.0, 3.14, 84_159_286, "#4a90d9"),
    2: (12_000_000, 0.0, 0.0, 0.0, 0.0, 1.7, 2_429_559, "#9a9a9a"),
    3: (47_000_000, 0.0, 6.0, 78.0, 38.0, 0.9, 2_247_428, "#9fe0c8"),
    4: (5_263_138_304, 0.2, 7.0, 70.0, 15.0, 3.14, 9_646_663, "#b07850"),
    5: (9_832_684_544, 0.01, 2.1, 15.0, 0.0, 3.14, 85_109_365, "#a050d0"),
    6: (20_726_155_264, 0.051, 0.06, 135.5, 0.0, 3.14, 47_921_949, "#d0603a"),
    7: (3_200_000, 0.03, 0.2, 0.0, 0.0, 1.7, 1_049_599, "#8a8a8a"),
    8: (68_773_560_320, 0.05, 1.304, 52.0, 0.0, 0.1, 2_455_985_200, "#6ab04c"),
    9: (27_184_000, 0.0, 0.0, 0.0, 0.0, 3.14, 3_723_646, "#4a7fb0"),
    10: (43_152_000, 0.0, 0.0, 0.0, 0.0, 0.9, 2_406_401, "#a8c8e0"),
    11: (128_500_000, 0.235, 15.0, 10.0, 25.0, 0.9, 1_221_061, "#8a7050"),
    12: (68_500_000, 0.0, 0.025, 0.0, 0.0, 3.14, 10_856_518, "#d8c8b0"),
    13: (31_500_000, 0.55, 12.0, 80.0, 10.0, 0.9, 126_123, "#a08070"),
    14: (179_890_000, 0.171, 4.25, 2.0, 15.0, 0.9, 1_042_139, "#d8d080"),
    15: (40_839_348_203, 0.145, 5.0, 280.0, 90.0, 3.14, 32_832_840, "#a0a0a0"),
    16: (90_118_820_000, 0.26, 6.15, 50.0, 260.0, 3.14, 119_082_940, "#d0d8e0"),
}
KERBIN_ORBIT = dict(zip(("SMA", "ECC", "INC", "LAN", "LPE", "MNA"), PLANET_ORBITS[1]), EPH=0, REF=0)
KERBIN_SOI = PLANET_ORBITS[1][6]

DAY, YEAR = 6 * 3600, 426 * 6 * 3600

# Kerbal XP (estimate): per body, the best activity across all recovered flights counts once.
XP_BODY = {"Kerbin": 1, "Sun": 4, "Kerbol": 4, "Mun": 2, "Minmus": 2.5, "Moho": 7, "Eve": 5,
           "Gilly": 6, "Duna": 5, "Ike": 5, "Dres": 6, "Jool": 6, "Laythe": 8, "Vall": 8,
           "Tylo": 8, "Bop": 8, "Pol": 8, "Eeloo": 10}
XP_ACTIVITY = {"Flyby": 1.0, "Orbit": 1.5, "Land": 2.3, "PlantFlag": 2.5}
XP_HOME = {"Orbit": 1.0}  # Kerbin itself: only reaching orbit counts
XP_LEVELS = [0, 2, 8, 16, 32, 64]

# part name (without .v2 suffix) -> (label, power, relay?)
ANTENNAS = {
    "longAntenna": ("Communotron 16", 5e5, False),
    "SurfAntenna": ("Communotron 16-S", 5e5, False),
    "HighGainAntenna5": ("HG-5", 5e6, True),
    "mediumDishAntenna": ("DTS-M1", 2e9, False),
    "RelayAntenna5": ("RA-2", 2e9, True),
    "HighGainAntenna": ("HG-55", 15e9, False),
    "RelayAntenna50": ("RA-15", 15e9, True),
    "commDish": ("Communotron 88-88", 100e9, False),
    "RelayAntenna100": ("RA-100", 100e9, True),
}
# part name -> (label, vacuum Isp s, propellant group, vacuum thrust kN)
ENGINES = {
    "liquidEngine": ("Reliant", 310, "LFO", 240), "liquidEngine2": ("Swivel", 320, "LFO", 215),
    "liquidEngine3": ("Terrier", 345, "LFO", 60), "liquidEngine2-2": ("Poodle", 350, "LFO", 250),
    "liquidEngineMini": ("Spark", 320, "LFO", 20), "microEngine": ("Ant", 315, "LFO", 2),
    "radialEngineMini": ("Spider", 290, "LFO", 2), "smallRadialEngine": ("Twitch", 290, "LFO", 16),
    "radialLiquidEngine1-2": ("Thud", 305, "LFO", 120), "toroidalAerospike": ("Dart", 340, "LFO", 180),
    "engineLargeSkipper": ("Skipper", 320, "LFO", 650), "liquidEngineMainsail": ("Mainsail", 310, "LFO", 1500),
    "Size2LFB": ("Twin-Boar", 300, "LFO", 2000), "Size3EngineCluster": ("Mammoth", 315, "LFO", 4000),
    "Size3AdvancedEngine": ("Rhino", 340, "LFO", 2000), "SSME": ("Vector", 315, "LFO", 1000),
    "LiquidEngineLV-T91": ("Cheetah", 355, "LFO", 125), "LiquidEngineLV-TX87": ("Bobcat", 310, "LFO", 400),
    "LiquidEngineRK-7": ("Kodiak", 317, "LFO", 260), "LiquidEngineRV-1": ("Cub", 317, "LFO", 32),
    "nuclearEngine": ("LV-N Nerv", 800, "LF", 60), "ionEngine": ("Dawn", 4200, "Xenon", 2),
    "omsEngine": ("Puff", 250, "Mono", 20),
}
# propellant group -> units of each resource per unit burned (LF:Ox is 9:11)
PROPELLANTS = {"LFO": {"LiquidFuel": 0.9, "Oxidizer": 1.1}, "LF": {"LiquidFuel": 1},
               "Xenon": {"XenonGas": 1}, "Mono": {"MonoPropellant": 1}}
# part modules that split the craft when staged: decouplers, separators, launch clamps
SEPARATORS = {"ModuleDecouple", "ModuleAnchoredDecoupler", "LaunchClamp"}
G0 = 9.80665
DENSITY = {"LiquidFuel": 0.005, "Oxidizer": 0.005, "MonoPropellant": 0.004, "XenonGas": 0.0001,
           "Ore": 0.01, "SolidFuel": 0.0075, "Ablator": 0.001}
SHOW_RES = ["LiquidFuel", "Oxidizer", "MonoPropellant", "XenonGas", "Ore", "ElectricCharge"]
RES_SHORT = {"LiquidFuel": "LF", "Oxidizer": "Ox", "MonoPropellant": "Mono", "XenonGas": "Xe",
             "Ore": "Ore", "ElectricCharge": "EC"}
MINOR_TYPES = {"Debris", "Flag", "SpaceObject", "DeployedScienceController", "DeployedSciencePart",
               "DroppedPart", "Unknown"}
PARAM_KEYS = ["title", "targetBody", "targetType", "body", "situation", "vesselName", "partNames",
              "partName", "minAltitude", "maxAltitude", "targetName", "location", "scanName", "coverage"]

# ---------------------------------------------------------------- ConfigNode parser


class Node:
    __slots__ = ("name", "values", "children")

    def __init__(self, name):
        self.name, self.values, self.children = name, [], []

    def get(self, key, default=None):
        for k, v in self.values:
            if k == key:
                return v
        return default

    def getall(self, key):
        return [v for k, v in self.values if k == key]

    def nodes(self, name):
        return [c for c in self.children if c.name == name]

    def node(self, name):
        for c in self.children:
            if c.name == name:
                return c
        return None


def parse(text):
    root = Node("root")
    stack, pending = [root], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line == "{":
            n = Node(pending or "")
            stack[-1].children.append(n)
            stack.append(n)
            pending = None
        elif line == "}":
            stack.pop()
        elif "=" in line:
            k, _, v = line.partition("=")
            stack[-1].values.append((k.strip(), v.strip()))
        else:
            pending = line
    return root.children[0] if root.children else root


# ---------------------------------------------------------------- helpers


def f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def base_part(name):
    return re.sub(r"\.v\d+$", "", name or "")


def body_name(x):
    """Body from a save field: stock contracts store its index, ContractConfigurator its name."""
    if not x:
        return None
    return BODIES.get(int(x), ("?",))[0] if x.isdigit() else x


def ksp_date(ut):
    y, rem = divmod(ut, YEAR)
    d, rem = divmod(rem, DAY)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    return f"Y{int(y) + 1} D{int(d) + 1} {int(h):02d}:{int(m):02d}:{int(s):02d}"


def ksp_dur(t):
    if t is None or not math.isfinite(t):
        return "—"
    if t < 0:
        return "-" + ksp_dur(-t)
    y, rem = divmod(t, YEAR)
    d, rem = divmod(rem, DAY)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if y:
        parts.append(f"{int(y)}y")
    if d or y:
        parts.append(f"{int(d)}d")
    parts.append(f"{int(h)}h {int(m):02d}m {s:04.1f}s")
    return " ".join(parts)


def dist(m):
    if m is None or not math.isfinite(m):
        return "—"
    a = abs(m)
    if a >= 1e9:
        return f"{m / 1e9:,.3f} Gm"
    if a >= 1e6:
        return f"{m / 1e6:,.1f} Mm"
    return f"{m / 1e3:,.1f} km"


def orbit_info(o):
    ref = int(f(o.get("REF")))
    _, R, GM, atm, _ = BODIES.get(ref, ("?", 0, 0, 0, None))
    a, e = f(o.get("SMA")), f(o.get("ECC"))
    info = dict(body=BODIES.get(ref, ("?",))[0], ref=ref, SMA=a, ECC=e, INC=f(o.get("INC")),
                LAN=f(o.get("LAN")), LPE=f(o.get("LPE")), MNA=f(o.get("MNA")), EPH=f(o.get("EPH")))
    if a > 0 and e < 1 and GM:
        info["ap_alt"] = a * (1 + e) - R
        info["pe_alt"] = a * (1 - e) - R
        info["period_s"] = 2 * math.pi * math.sqrt(a ** 3 / GM)
    else:
        info["ap_alt"] = math.inf
        info["pe_alt"] = (a * (1 - e) - R) if a and GM else None
        info["period_s"] = None
    return info


def state_vector(el, ut, GM):
    """Position and velocity (3D, parent frame) of an elliptical orbit at time ut."""
    a, e = el["SMA"], el["ECC"]
    n = math.sqrt(GM / a ** 3)
    M = el["MNA"] + n * (ut - el["EPH"])
    E = M
    for _ in range(50):
        E -= (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
    nu = 2 * math.atan2(math.sqrt(1 + e) * math.sin(E / 2), math.sqrt(1 - e) * math.cos(E / 2))
    p = a * (1 - e * e)
    r = p / (1 + e * math.cos(nu))
    h = math.sqrt(GM * p)
    i, O, w = (math.radians(el[k]) for k in ("INC", "LAN", "LPE"))
    px, py = r * math.cos(nu), r * math.sin(nu)
    vx, vy = -GM / h * math.sin(nu), GM / h * (e + math.cos(nu))
    cO, sO, ci, si, cw, sw = math.cos(O), math.sin(O), math.cos(i), math.sin(i), math.cos(w), math.sin(w)
    R = ((cO * cw - sO * sw * ci, -cO * sw - sO * cw * ci),
         (sO * cw + cO * sw * ci, -sO * sw + cO * cw * ci),
         (sw * si, cw * si))
    pos = tuple(R[k][0] * px + R[k][1] * py for k in range(3))
    vel = tuple(R[k][0] * vx + R[k][1] * vy for k in range(3))
    return pos, vel


def elements_from_state(pos, vel, ut, GM, ref):
    """Classical elements (KSP field names) from a state vector; None if not elliptical."""
    cross = lambda a, b: (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    dot = lambda a, b: sum(x * y for x, y in zip(a, b))
    r, v2 = math.sqrt(dot(pos, pos)), dot(vel, vel)
    h = cross(pos, vel)
    hn = math.sqrt(dot(h, h))
    a = 1 / (2 / r - v2 / GM)
    evec = tuple(c / GM - p / r for c, p in zip(cross(vel, h), pos))
    e = math.sqrt(dot(evec, evec))
    if a <= 0 or e >= 1:
        return None
    inc = math.acos(max(-1, min(1, h[2] / hn)))
    nvec = (-h[1], h[0], 0.0)
    nn = math.hypot(nvec[0], nvec[1])
    O = math.atan2(nvec[1], nvec[0]) if nn > 1e-9 else 0.0
    if nn < 1e-9:  # equatorial: measure from x-axis
        nvec, nn = (1.0, 0.0, 0.0), 1.0
    w = math.atan2(dot(cross(nvec, evec), h) / hn, dot(nvec, evec)) if e > 1e-12 else 0.0
    ref_dir = evec if e > 1e-12 else nvec
    nu = math.atan2(dot(cross(ref_dir, pos), h) / hn, dot(ref_dir, pos))
    E = 2 * math.atan2(math.sqrt(1 - e) * math.sin(nu / 2), math.sqrt(1 + e) * math.cos(nu / 2))
    return dict(SMA=a, ECC=e, INC=math.degrees(inc), LAN=math.degrees(O) % 360,
                LPE=math.degrees(w) % 360, MNA=E - e * math.sin(E), EPH=ut, REF=ref)


def maneuvers(v, orb, ut):
    """Planned maneuver nodes, chained: each burn is applied to the orbit left by the previous one."""
    fp = v.node("FLIGHTPLAN")
    out = []
    el = {k: orb[k] for k in ("SMA", "ECC", "INC", "LAN", "LPE", "MNA", "EPH")} if orb else None
    ref = orb.get("ref") if orb else None
    for m in fp.nodes("MANEUVER") if fp else []:
        t = f(m.get("UT"))
        radial, normal, prograde = (f(x) for x in (m.get("dV") or "0,0,0").split(","))
        node = dict(ut=t, date=ksp_date(t), time_until_s=t - ut, prograde=prograde, normal=normal,
                    radial=radial, total=math.sqrt(radial ** 2 + normal ** 2 + prograde ** 2), after=None)
        if el and ref in BODIES and el["SMA"] > 0 and el["ECC"] < 1:
            GM = BODIES[ref][2]
            pos, vel = state_vector(el, t, GM)
            vn = math.sqrt(sum(c * c for c in vel))
            pro = tuple(c / vn for c in vel)
            h = (pos[1] * vel[2] - pos[2] * vel[1], pos[2] * vel[0] - pos[0] * vel[2], pos[0] * vel[1] - pos[1] * vel[0])
            hn = math.sqrt(sum(c * c for c in h))
            nrm = tuple(c / hn for c in h)
            rad = (pro[1] * nrm[2] - pro[2] * nrm[1], pro[2] * nrm[0] - pro[0] * nrm[2], pro[0] * nrm[1] - pro[1] * nrm[0])
            vel2 = tuple(vel[k] + prograde * pro[k] + normal * nrm[k] + radial * rad[k] for k in range(3))
            el = elements_from_state(pos, vel2, t, GM, ref)
            if el:
                after = orbit_info(el)
                if ref == 0:
                    after["kerbin_relative_at_burn"] = kerbin_relative(after, t)
                node["after"] = after
        else:
            el = None
        out.append(node)
    return out


def kerbin_relative(el, ut):
    GM = BODIES[0][2]
    if el["SMA"] <= 0 or el["ECC"] >= 1:
        return None
    p = state_vector(el, ut, GM)[0]
    k = state_vector(KERBIN_ORBIT, ut, GM)[0]
    d = math.dist(p, k)
    phase = (math.degrees(math.atan2(p[1], p[0]) - math.atan2(k[1], k[0])) + 180) % 360 - 180
    tk = 2 * math.pi * math.sqrt(KERBIN_ORBIT["SMA"] ** 3 / GM)
    return dict(distance_m=d, phase_deg=phase, in_kerbin_soi=d < KERBIN_SOI,
                period_minus_kerbin_s=2 * math.pi * math.sqrt(el["SMA"] ** 3 / GM) - tk,
                radial_offset_m=math.hypot(p[0], p[1]) - math.hypot(k[0], k[1]))


# ---------------------------------------------------------------- extraction


def career(game):
    out = {}
    for sc in game.nodes("SCENARIO"):
        name = sc.get("name")
        if name == "Funding":
            out["funds"] = f(sc.get("funds"))
        elif name == "Reputation":
            out["reputation"] = f(sc.get("rep"))
        elif name == "ResearchAndDevelopment":
            out["science"] = f(sc.get("sci"))
            out["techs_unlocked"] = sum(1 for t in sc.nodes("Tech") if t.get("state") == "Available")
        elif name == "ScenarioUpgradeableFacilities":
            out["facilities"] = {c.name.split("/")[-1]: 1 + round(f(c.get("lvl")) * 2)
                                 for c in sc.children}
    return out


def kerbal_xp(entries):
    """entries: list of 'Activity,Body' strings. Returns (xp, {body: best_activity})."""
    best = {}
    for ent in entries:
        act, _, body = ent.partition(",")
        if not body:
            continue
        table = XP_HOME if body == "Kerbin" else XP_ACTIVITY
        val = table.get(act, 0) * XP_BODY.get(body, 0)
        if val and val > best.get(body, (0, ""))[0]:
            best[body] = (val, act)
    return sum(v for v, _ in best.values()), {b: a for b, (_, a) in best.items()}


def level_for(xp):
    return max(i for i, t in enumerate(XP_LEVELS) if xp >= t - 1e-9)


def kerbals(game, crew_map):
    roster = game.node("ROSTER")
    out = []
    for k in roster.nodes("KERBAL") if roster else []:
        if k.get("type") == "Applicant":
            continue
        name = k.get("name")
        cl = k.node("CAREER_LOG")
        fl = k.node("FLIGHT_LOG")
        career_entries = [v for key, v in cl.values if key.isdigit()] if cl else []
        flight_entries = [v for key, v in fl.values if key.isdigit()] if fl else []
        extra = f(k.get("extraXP"))
        xp, visited = kerbal_xp(career_entries)
        xp_if_recovered, _ = kerbal_xp(career_entries + flight_entries)
        out.append(dict(
            name=name, trait=k.get("trait"), type=k.get("type"), state=k.get("state"),
            vessel=crew_map.get(name), veteran=k.get("veteran") == "True",
            xp=xp + extra, level=level_for(xp + extra),
            xp_if_recovered_now=xp_if_recovered + extra,
            level_if_recovered_now=level_for(xp_if_recovered + extra),
            flights=int(f(cl.get("flight"))) if cl else 0,
            best_by_body=visited,
        ))
    return out


def separates_at(p):
    """Stage in which this part splits the craft (an armed decoupler or launch clamp), else None."""
    for m in p.nodes("MODULE"):
        if (m.get("name") in SEPARATORS and m.get("isDecoupled") != "True"
                and m.get("stagingEnabled") != "False"):  # heat shields: staging off
            return int(f(p.get("istg")))
    return None


def stage_dv(parts):
    """Vacuum Δv per stage, from the part tree (`parent`) and the staging order (`istg`).

    A part leaves the craft when the first separator between it and the root part fires.
    Each stage burns the propellant in the parts it is about to drop, with the engines lit by
    then; the last stage burns what is left with every remaining engine. Simplified: no
    fuel-flow rules, solid boosters are dead weight.
    """
    n = len(parts)
    names = [base_part(p.get("name")) for p in parts]
    parent = [int(f(p.get("parent"))) for p in parts]
    istg = [int(f(p.get("istg"))) for p in parts]
    sep = [separates_at(p) for p in parts]
    mass = [f(p.get("mass")) + sum(DENSITY.get(r.get("name"), 0) * f(r.get("amount")) for r in p.nodes("RESOURCE"))
            for p in parts]
    drop = []  # stage in which each part leaves the craft; -1 = never
    for i in range(n):
        d, j = -1, i
        for _ in range(n):  # walk up to the root part (its parent is itself)
            if sep[j] is not None:
                d = max(d, sep[j])
            if parent[j] == j:
                break
            j = parent[j]
        drop.append(d)
    engines = [i for i in range(n) if names[i] in ENGINES]
    events = {istg[i] for i in engines} | {s for s in sep if s is not None}

    stages = []
    for d in sorted(set(drop), reverse=True):
        m = start = sum(mass[i] for i in range(n) if drop[i] <= d)
        fuel = {}
        for i in range(n):
            if drop[i] == d:
                for r in parts[i].nodes("RESOURCE"):
                    fuel[r.get("name")] = fuel.get(r.get("name"), 0) + f(r.get("amount"))
        lit = [i for i in engines if drop[i] <= d and (istg[i] > d or d < 0)]
        dv, used = 0.0, []
        for group, mix in PROPELLANTS.items():
            engs = [ENGINES[names[i]] for i in lit if ENGINES[names[i]][2] == group]
            units = min(fuel.get(r, 0) / k for r, k in mix.items())
            burned = units * sum(k * DENSITY[r] for r, k in mix.items())
            if not engs or units <= 0 or burned >= m:
                continue
            for r, k in mix.items():
                fuel[r] -= units * k
            isp = sum(e[3] for e in engs) / sum(e[3] / e[1] for e in engs)  # thrust-weighted
            dv += isp * G0 * math.log(m / (m - burned))
            m -= burned
            used += [e[0] for e in engs]
        if dv >= 1:
            count = {e: used.count(e) for e in dict.fromkeys(used)}
            stages.append(dict(stage=min((s for s in events if s > d), default=d + 1),
                               engines=[f"{k}× {e}" if k > 1 else e for e, k in count.items()],
                               dv_ms=round(dv), mass_t=round(start, 2)))
    return stages


def vessel(v, ut):
    o = v.node("ORBIT")
    orb = orbit_info(o) if o else {}
    crew, res = [], {}
    dry = 0.0
    antennas, engines, labs, ports = [], [], [], 0
    lab_data = 0.0
    stored_data = 0
    for p in v.nodes("PART"):
        pname = base_part(p.get("name"))
        dry += f(p.get("mass"))
        crew += p.getall("crew")
        if pname in ANTENNAS:
            antennas.append(ANTENNAS[pname][0])
        if pname in ENGINES:
            engines.append(ENGINES[pname][0])
        if "dockingPort" in pname:
            ports += 1
        for r in p.nodes("RESOURCE"):
            rn = r.get("name")
            cur, mx = f(r.get("amount")), f(r.get("maxAmount"))
            a = res.setdefault(rn, [0.0, 0.0])
            a[0] += cur
            a[1] += mx
        for m in p.nodes("MODULE"):
            mn = m.get("name")
            if mn == "ModuleScienceLab":
                labs.append(pname)
                lab_data += f(m.get("dataStored"))
            stored_data += len(m.nodes("ScienceData"))
    wet = dry + sum(DENSITY.get(k, 0) * a[0] for k, a in res.items())
    stages = stage_dv(v.nodes("PART"))
    out = dict(
        pid=v.get("pid"), name=v.get("name"), type=v.get("type"), situation=v.get("sit"),
        landed_at=v.get("displaylandedAt") or v.get("landedAt") or None,
        lat=f(v.get("lat")), lon=f(v.get("lon")), alt=f(v.get("alt")),
        mission_time_s=f(v.get("met")), crew=crew, orbit=orb,
        parts_count=len(v.nodes("PART")), dry_mass_t=round(dry, 3), wet_mass_t=round(wet, 3),
        resources={k: [round(a[0], 1), round(a[1], 1)] for k, a in res.items()},
        antennas=antennas, engines=engines,
        dv_stages=stages, dv_total_ms=sum(s["dv_ms"] for s in stages),
        labs=len(labs), lab_data=round(lab_data, 1), stored_science_items=stored_data,
        docking_ports=ports,
    )
    if orb.get("ref") == 0:
        out["kerbin_relative"] = kerbin_relative(orb, ut)
    out["maneuvers"] = maneuvers(v, orb, ut)
    tgt = v.node("TARGET")
    out["target"] = tgt.get("tgtId") or tgt.get("vesselId") if tgt else None
    disc = v.node("DISCOVERY")
    if v.get("type") == "SpaceObject" and disc:
        size, tracked = int(f(disc.get("size"))), int(f(disc.get("state"))) > 1  # state 1 = presence only (untracked)
        out["asteroid"] = dict(size_class="ABCDEFGHI"[size] if 0 <= size < 9 else "?", tracked=tracked,
                               lost_in_s=None if tracked else f(disc.get("lastObservedTime")) + f(disc.get("lifetime")) - ut)
    return out


def alarms(game, fs, ut):
    """KSP Alarm Clock entries, with the vessel name resolved from its persistentId."""
    names = {v.get("persistentId"): v.get("name") for v in fs.nodes("VESSEL")}
    out = []
    for sc in game.nodes("SCENARIO"):
        if sc.get("name") != "AlarmClockScenario":
            continue
        al = sc.node("ALARMS")
        for a in al.nodes("ALARM") if al else []:
            t = f(a.get("ut"))
            out.append(dict(title=a.get("title"), type=(a.get("type") or "").replace("AlarmType", ""),
                            description=a.get("description") or "", vessel=names.get(a.get("vesselId")),
                            ut=t, date=ksp_date(t), time_until_s=t - ut,
                            triggered=a.get("triggered") == "True",
                            maneuver_ut=f(a.get("maneuverUT")) or None))
    return sorted(out, key=lambda a: a["ut"])


def deployed_science(game, fs):
    """Breaking Ground experiments per body: science generated vs its limit, and data waiting to be sent."""
    names = {v.get("pid"): v.get("name") for v in fs.nodes("VESSEL")}
    part_vessel = {p.get("persistentId"): v.get("pid") for v in fs.nodes("VESSEL") for p in v.nodes("PART")}
    out = []
    for sc in game.nodes("SCENARIO"):
        if sc.get("name") != "DeployedScience":
            continue
        clusters = sc.node("SCIENCECLUSTERS")
        for c in clusters.nodes("SCIENCECLUSTER") if clusters else []:
            parts = c.node("MANNEDSCIENCEPARTS")
            exps = []
            for mp in parts.nodes("MANNEDSCIENCEPART") if parts else []:
                for e in mp.nodes("EXPERIMENT"):
                    pid = (e.get("VesselId") or "").replace("-", "")  # experiment part's vessel pid
                    exps.append(dict(name=names.get(pid) or e.get("ExperimentId"), vessel_pid=pid,
                                     enabled=mp.get("Enabled") == "True",
                                     generated=round(f(e.get("TotalScienceGenerated")), 1),
                                     limit=round(f(e.get("ScienceLimit")), 1),
                                     transmitted=round(f(e.get("TransmittedScienceData")), 1),
                                     stored=round(f(e.get("StoredScienceData")), 1),
                                     no_comms=e.get("noCommNetMsgPosted") == "True",
                                     no_power=e.get("noPowerMsgPosted") == "True"))
            out.append(dict(body=c.get("DeployedBody"), controller_pid=part_vessel.get(c.get("ControlModulePartId")),
                            experiments=exps))
    return out


def contracts(game, ut):
    out = []
    for sc in game.nodes("SCENARIO"):
        if sc.get("name") != "ContractSystem":
            continue
        cs = sc.node("CONTRACTS")
        for c in cs.nodes("CONTRACT") if cs else []:
            st = c.get("state")
            if st not in ("Active", "Offered"):
                continue
            vals = [f(x) for x in (c.get("values") or "").split(",")]
            vals += [0.0] * (12 - len(vals))
            params = []
            for p in c.nodes("PARAM"):
                extra = {k: p.get(k) for k in PARAM_KEYS if p.get(k)}
                if "targetBody" in extra:
                    extra["targetBody"] = body_name(extra["targetBody"])
                params.append(dict(name=p.get("name"), state=p.get("state"), **extra))
            deadline = vals[10] if st == "Active" else vals[8]
            out.append(dict(
                type=c.get("type"), state=st, agent=c.get("agent"),
                title=(c.get("title") or "").rstrip(".") or None,  # ContractConfigurator only
                target_body=body_name(c.get("targetBody")),
                funds_advance=vals[2], funds_completion=vals[3], funds_failure=vals[4],
                science=vals[5], rep_completion=vals[6], rep_failure=vals[7],
                deadline_ut=deadline or None,
                time_left_s=(deadline - ut) if deadline else None,
                params=params,
            ))
    return out


# ---------------------------------------------------------------- markdown


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out


def render(d, show_all):
    L = []
    h = d["header"]
    L += [f"# KSP digest — {h['title']}", "",
          f"**{h['mode']} · KSP {h['version']} · UT {h['ut']:,.0f} s = {h['date']}**  ",
          f"Source: `{h['file']}` (modified {h['mtime']})", ""]

    c = d["career"]
    L += ["## Career", "",
          f"Funds **{c.get('funds', 0):,.0f}** · Science **{c.get('science', 0):,.1f}** · "
          f"Reputation **{c.get('reputation', 0):,.1f}** · Techs unlocked {c.get('techs_unlocked', 0)}", ""]
    fac = c.get("facilities", {})
    L += ["Facilities: " + " · ".join(f"{k} L{v}" for k, v in fac.items()), ""]

    L += ["## Kerbals", "", "_XP/level are computed from flight logs (estimate); "
          "'if recovered' includes the current unrecovered flight._", ""]
    rows = []
    for k in sorted(d["kerbals"], key=lambda k: (k["state"] != "Assigned", -k["xp"], k["name"])):
        where = k["vessel"] or ""
        pending = (f"L{k['level_if_recovered_now']} ({k['xp_if_recovered_now']:g})"
                   if k["xp_if_recovered_now"] > k["xp"] else "")
        visited = ", ".join(f"{b}:{a}" for b, a in k["best_by_body"].items())
        rows.append((k["name"], k["trait"], k["state"], where, f"L{k['level']}", f"{k['xp']:g}",
                     pending, k["flights"], visited))
    L += md_table(["Name", "Trait", "State", "Vessel", "Lvl", "XP", "If recovered", "Flights",
                   "Best per body"], rows) + [""]

    major = [v for v in d["vessels"] if v["type"] not in MINOR_TYPES]
    minor = [v for v in d["vessels"] if v["type"] in MINOR_TYPES]
    shown = d["vessels"] if show_all else major
    L += ["## Vessels", ""]
    counts = {}
    for v in minor:
        counts[v["type"]] = counts.get(v["type"], 0) + 1
    if counts and not show_all:
        L += ["_Hidden (use --all): " + ", ".join(f"{n} {t}" for t, n in sorted(counts.items())) + "_", ""]

    by_body = {}
    for v in shown:
        by_body.setdefault(v["orbit"].get("ref", -1), []).append(v)
    for ref in BODY_ORDER + sorted(set(by_body) - set(BODY_ORDER)):
        vs = by_body.get(ref)
        if not vs:
            continue
        L += [f"### {BODIES.get(ref, ('Unknown',))[0]}", ""]
        for v in sorted(vs, key=lambda v: (v["situation"] != "ORBITING", v["name"])):
            o = v["orbit"]
            L.append(f"**{v['name']}** — {v['type']}, {v['situation']}"
                     + (f", crew: {', '.join(v['crew'])}" if v["crew"] else "")
                     + (f", target: {v['target']}" if v.get("target") else ""))
            if v["situation"] in ("LANDED", "SPLASHED", "PRELAUNCH"):
                L.append(f"- Position: lat {v['lat']:.3f}°, lon {v['lon']:.3f}°"
                         + (f", at {v['landed_at']}" if v["landed_at"] else ""))
            elif o:
                L.append(f"- Ap {dist(o['ap_alt'])} · Pe {dist(o['pe_alt'])} · inc {o['INC']:.2f}° · "
                         f"ecc {o['ECC']:.5f} · period {ksp_dur(o['period_s'])}")
            ast = v.get("asteroid")
            if ast:
                L.append(f"- Class {ast['size_class']}, " + ("tracked" if ast["tracked"]
                         else f"untracked: signal lost in {ksp_dur(ast['lost_in_s'])}"))
            kr = v.get("kerbin_relative")
            if kr:
                L.append(f"- vs Kerbin: {kr['phase_deg']:+.2f}° ({'ahead' if kr['phase_deg'] > 0 else 'behind'}), "
                         f"distance {dist(kr['distance_m'])}, radial offset {dist(kr['radial_offset_m'])}, "
                         f"period diff {kr['period_minus_kerbin_s']:+,.0f} s"
                         + (" — INSIDE Kerbin SOI" if kr["in_kerbin_soi"] else ""))
            res = " · ".join(f"{RES_SHORT[r]} {v['resources'][r][0]:g}/{v['resources'][r][1]:g}"
                             for r in SHOW_RES if r in v["resources"])
            if res:
                L.append(f"- Resources: {res}")
            bits = [f"{v['parts_count']} parts", f"{v['wet_mass_t']:g} t ({v['dry_mass_t']:g} t dry)"]
            if v["engines"]:
                bits.append("engines: " + ", ".join(sorted(set(v["engines"]))))
            if len(v["dv_stages"]) == 1:
                bits.append(f"Δv≈ {v['dv_total_ms']:,} m/s vac")
            if v["antennas"]:
                bits.append("antennas: " + ", ".join(sorted(set(v["antennas"]))))
            if v["labs"]:
                bits.append(f"lab ×{v['labs']} (data {v['lab_data']:g})")
            if v["stored_science_items"]:
                bits.append(f"{v['stored_science_items']} science results aboard")
            if v["docking_ports"]:
                bits.append(f"{v['docking_ports']} docking ports")
            L.append("- " + " · ".join(bits))
            if len(v["dv_stages"]) > 1:
                L.append(f"- Δv≈ {v['dv_total_ms']:,} m/s vac: " + " → ".join(
                    f"S{s['stage']} {s['dv_ms']:,} ({', '.join(s['engines'])})" for s in v["dv_stages"]))
            for i, m in enumerate(v.get("maneuvers", []), 1):
                when = (f"in {ksp_dur(m['time_until_s'])}" if m["time_until_s"] >= 0
                        else f"{ksp_dur(-m['time_until_s'])} AGO (missed)")
                L.append(f"- **Maneuver {i}** @ {m['date']} ({when}): Δv {m['total']:.1f} m/s = "
                         f"prograde {m['prograde']:+.1f}, normal {m['normal']:+.1f}, radial {m['radial']:+.1f}")
                a = m["after"]
                if a:
                    L.append(f"  - after: Ap {dist(a['ap_alt'])} · Pe {dist(a['pe_alt'])} · inc {a['INC']:.2f}° · "
                             f"ecc {a['ECC']:.5f} · period {ksp_dur(a['period_s'])}")
                    kr = a.get("kerbin_relative_at_burn")
                    if kr:
                        L.append(f"  - at burn vs Kerbin: {kr['phase_deg']:+.2f}°, distance {dist(kr['distance_m'])}, "
                                 f"period diff after burn {kr['period_minus_kerbin_s']:+,.0f} s")
                else:
                    L.append("  - after: (not predicted — escape/hyperbolic or follows an SOI change)")
            L.append("")

    rows = []
    for c in d.get("deployed_science", []):
        for e in c["experiments"]:
            state = ("n/a" if not e["limit"] else "done" if e["generated"] >= e["limit"] else "on" if e["enabled"] else "off")
            waiting = f"{e['stored']:g}" + (" (no link)" if e["no_comms"] and e["stored"] else "")
            rows.append((c["body"], e["name"], f"{e['generated']:g} / {e['limit']:g}", state,
                         f"{e['transmitted']:g}", waiting if e["stored"] else ""))
    if rows:
        L += ["## Deployed science", ""]
        L += md_table(["Body", "Experiment", "Generated / limit", "State", "Sent", "Waiting"], rows) + [""]

    if d.get("alarms"):
        L += ["## Alarm clock", ""]
        L += md_table(["When", "In", "Title", "Type", "Vessel"],
                      [(a["date"], ksp_dur(a["time_until_s"]), a["title"], a["type"], a["vessel"] or "")
                       for a in d["alarms"]]) + [""]

    act = [c for c in d["contracts"] if c["state"] == "Active"]
    off = [c for c in d["contracts"] if c["state"] == "Offered"]
    L += ["## Contracts", "", f"### Active ({len(act)})", ""]
    for c in act:
        left = ksp_dur(c["time_left_s"]) if c["time_left_s"] else "no deadline"
        L.append(f"**{c['title'] or c['type']}** — {c['agent']}" + (f" · {c['target_body']}" if c["target_body"] else "")
                 + f" · reward {c['funds_completion']:,.0f} funds / {c['science']:g} sci / {c['rep_completion']:g} rep"
                 + f" · time left: {left}")
        for p in c["params"]:
            if "scanName" in p:  # SCANsat coverage target
                text = f"{p['scanName']} ≥{p.get('coverage', '?')}% · {p['state']}"
            else:
                extra = ", ".join(f"{k}={v}" for k, v in p.items() if k not in ("name", "state"))
                text = p["name"] + (f" ({extra})" if extra else "")
            L.append(f"- [{'x' if p['state'] == 'Complete' else ' '}] {text}")
        L.append("")
    L += [f"### Offered ({len(off)})", ""]
    L += md_table(["Type", "Body", "Funds", "Sci", "Rep", "Agent"],
                  [(c["title"] or c["type"], c["target_body"] or "", f"{c['funds_completion']:,.0f}", f"{c['science']:g}",
                    f"{c['rep_completion']:g}", c["agent"]) for c in off]) + [""]
    return "\n".join(L)


# ---------------------------------------------------------------- main

def find_live_save():
    """$KSP_SAVE, else the most recently written saves/*/persistent.sfs under $KSP_DIR."""
    if os.environ.get("KSP_SAVE"):
        return Path(os.environ["KSP_SAVE"]).expanduser()
    ksp_dir = Path(os.environ.get("KSP_DIR") or DEFAULT_KSP_DIR).expanduser()
    found = [p for p in (ksp_dir / "saves").glob("*/persistent.sfs")
             if p.parent.name not in ("scenarios", "training")]
    return max(found, key=lambda p: p.stat().st_mtime) if found else None


def planets():
    out = []
    for idx, (name, R, GM, atm, parent) in BODIES.items():
        o = PLANET_ORBITS.get(idx)
        d = dict(idx=idx, name=name, radius=R, GM=GM, atm=atm, parent=parent,
                 color=o[7] if o else "#ffd34d", soi=o[6] if o else None, orbit=None)
        if o:
            d["orbit"] = dict(SMA=o[0], ECC=o[1], INC=o[2], LAN=o[3], LPE=o[4], MNA=o[5], EPH=0.0, REF=parent)
        out.append(d)
    return out


def clean(x):
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    return x


def build(save, show_all):
    game = parse(save.read_text(encoding="utf-8", errors="replace"))
    fs = game.node("FLIGHTSTATE")
    if fs is None:
        raise ValueError("no FLIGHTSTATE in save (partial write?)")
    ut = f(fs.get("UT"))
    vessels = [vessel(v, ut) for v in fs.nodes("VESSEL")]
    crew_map = {c: v["name"] for v in vessels for c in v["crew"]}

    data = dict(
        header=dict(title=game.get("Title"), mode=game.get("Mode"), version=game.get("version"),
                    ut=ut, date=ksp_date(ut), file=save.name,
                    mtime=dt.datetime.fromtimestamp(save.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    mtime_epoch=save.stat().st_mtime,  # timezone-free; the dashboard's age indicator uses this
                    generated_at=dt.datetime.now().isoformat(timespec="seconds")),
        career=career(game),
        kerbals=kerbals(game, crew_map),
        vessels=vessels,
        contracts=contracts(game, ut),
        alarms=alarms(game, fs, ut),
        deployed_science=deployed_science(game, fs),
        planets=planets(),
    )

    md = render(data, show_all)
    DATA.mkdir(exist_ok=True)
    (DATA / "digest.md").write_text(md, encoding="utf-8")
    js = json.dumps(clean(data), indent=1)
    (DATA / "digest.json").write_text(js, encoding="utf-8")
    tmp = DATA / "digest.js.tmp"
    tmp.write_text("window.DIGEST = " + js + ";\n", encoding="utf-8")
    tmp.replace(DATA / "digest.js")  # atomic swap so the dashboard never reads half a file
    major = sum(1 for v in vessels if v["type"] not in MINOR_TYPES)
    print(f"[{dt.datetime.now():%H:%M:%S}] {save.name} @ {data['header']['date']}: {major} vessels "
          f"({len(vessels)} incl. minor), {len(data['kerbals'])} kerbals, "
          f"{sum(c['state'] == 'Active' for c in data['contracts'])} active contracts "
          f"→ digest.md ({md.count(chr(10)) + 1} lines), digest.json, digest.js", flush=True)


def serve(port):
    """Serve this folder on localhost in a background thread, without per-request log lines."""
    import functools
    import threading
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Quiet, directory=str(ROOT)))
    except OSError as e:
        raise SystemExit(f"cannot serve on port {port}: {e} (another server already running? stop it or use --serve PORT)")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"Dashboard: http://localhost:{port}/web/dashboard.html", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--save", type=Path, help="path to .sfs (default: newest *.sfs in saves/, "
                                              "else KSP's live persistent.sfs; with --watch: always the live save)")
    ap.add_argument("--all", action="store_true", help="include debris, flags, asteroids, deployed science")
    ap.add_argument("--watch", nargs="?", const=5.0, type=float, metavar="SECONDS",
                    help="keep running; regenerate whenever the save changes (poll interval, default 5 s)")
    ap.add_argument("--serve", nargs="?", const=8765, type=int, metavar="PORT",
                    help="also serve dashboard.html on http://localhost:PORT (default 8765); implies --watch")
    args = ap.parse_args()
    if args.serve and not args.watch:
        args.watch = 5.0

    save = args.save
    if save is None and not args.watch:
        snapshots = sorted(SAVES.glob("*.sfs"), key=lambda p: p.stat().st_mtime, reverse=True)
        save = snapshots[0] if snapshots else None
    if save is None:
        save = find_live_save()
        if save is None:
            ap.error("no KSP save found — set KSP_SAVE=/path/to/persistent.sfs or KSP_DIR=/path/to/KSP")
    if not save.exists():
        ap.error(f"save not found: {save}")

    if not args.watch:
        build(save, args.all)
        return

    import time
    if args.serve:
        serve(args.serve)
    print(f"Watching {save} every {args.watch:g}s — Ctrl+C to stop", flush=True)
    last = None
    try:
        while True:
            try:
                m = save.stat().st_mtime
            except FileNotFoundError:
                m = None
            if m is not None and m != last:
                time.sleep(1)  # let KSP finish writing
                for attempt in (1, 2):
                    try:
                        build(save, args.all)
                        last = m
                        break
                    except Exception as e:  # mid-write or truncated file
                        if attempt == 2:
                            print(f"[{dt.datetime.now():%H:%M:%S}] parse failed, will retry: {e}", flush=True)
                        time.sleep(2)
            time.sleep(args.watch)
    except KeyboardInterrupt:
        print("stopped")


if __name__ == "__main__":
    main()
