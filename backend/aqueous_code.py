# aqueous_code.py
# Plotly JSON dermal absorption model that uses your existing data_loader.py
# (DO NOT modify data_loader.py — we import its globals as-is)

import math
import argparse
import numpy as np
import pandas as pd
from scipy import optimize
import plotly.graph_objects as go
import plotly.io as pio
import os
import json

# Import your loader (unchanged)
from data_loader import compound_db, nameToCompound

# ---------------------- helpers: lookups & AEGL pick ----------------------
def pickAegl(rowDict, aeglTier, duration):
    """
    rowDict is a dict-like (from your DataFrame row).
    Expects columns like AEGL1_8hr, AEGL2_60min, etc.
    Returns mg/m^3 (float).
    """
    col = f"AEGL{aeglTier}_{duration}"
    if col not in rowDict:
        raise ValueError(f"AEGL column '{col}' not found in row.")
    val = rowDict[col]
    if pd.isna(val):
        raise ValueError(f"AEGL value missing for '{col}'.")
    return float(val)

def getCompoundByName(name):
    # exact key match first (as loader built nameToCompound with original case)
    if name in nameToCompound:
        return nameToCompound[name]
    # otherwise try case-insensitive match against the DataFrame
    hit = compound_db[compound_db["Name"].str.strip().str.lower() == str(name).strip().lower()]
    if hit.empty:
        raise ValueError(f"Chemical with Name='{name}' not found in database.")
    return hit.iloc[0].to_dict()

def getCompoundByCas(cas):
    hit = compound_db[compound_db["CAS"].astype(str).str.strip() == str(cas).strip()]
    if hit.empty:
        raise ValueError(f"Chemical with CAS='{cas}' not found in database.")
    return hit.iloc[0].to_dict()

# ---------------------- parameter builder (from row dict) ----------------------
def initParamsFromRow(row, aeglMgPerM3, bodyWeightKg=70.0, exposedFraction=0.10):
    """
    Build model parameters using the row (dict) from your DB and the chosen AEGL (mg/m^3).
    Units assumed:
      - MW: g/mol
      - logP: unitless (treated as logKow)
      - henryConstant: atm·m^3/mol (optional)
      - solubility: mg/L (optional)
      - vaporPressure: Pa (optional)
    """
    mw = float(row["MW"])
    logKow = float(row["logP"])
    kow = 10 ** logKow

    # Kscw per your formula
    kscw = 0.04 * (kow ** 0.81) + 4.06 * (kow ** 0.27) + 0.359

    # Treat AEGL (mg/m^3) as input air concentration like earlier workflow
    concComptox = float(aeglMgPerM3)    # mg/m^3
    csPpm = concComptox * 24.45 / mw    # ppm at STP (not used downstream but kept)
    cv = (10 ** -6) * concComptox       # mg/mL from mg/m^3

    # SC geometry & transport
    hsc = 10 * 0.0001                   # 0.001 cm
    h1 = hsc
    logPscw = -2.8 + (0.66 * logKow) - (0.0056 * mw)
    pscw = 10 ** logPscw                # cm/hr
    dsc = pscw * h1 / kscw              # cm^2/hr

    # Gas/water partition from Henry’s constant if present
    r = 0.0821
    t = 298.15
    H = row.get("henryConstant")
    if H is not None and pd.notna(H) and float(H) > 0.0:
        H = float(H)                    # atm·m^3/mol
        hcp = (1.0 / H) / 1000.0        # convert m^3 to L
        kwg = hcp * r * t               # water:gas
    else:
        # mild fallback so the model runs without H (provide H to improve realism)
        hcp = 1.0 / 1000.0
        kwg = hcp * r * t

    kscg = kscw * kwg                   # SC:air

    # Exposed area (fraction of adult surface area)
    bodySurfaceAreaCm2 = 18150
    a1 = exposedFraction * bodySurfaceAreaCm2

    return {
        "name": row.get("Name"),
        "cas": row.get("CAS"),
        "mw": mw, "bw": bodyWeightKg, "logKow": logKow, "kow": kow,
        "kscw": kscw, "concComptox": concComptox, "csPpm": csPpm, "cv": cv,
        "hsc": hsc, "h1": h1, "logPscw": logPscw, "pscw": pscw, "dsc": dsc,
        "r": r, "t": t, "kwg": kwg, "kscg": kscg,
        "nUp": 10, "bodySurfaceAreaCm2": bodySurfaceAreaCm2, "a1": a1
    }

# ---------------------- math helpers ----------------------
def seriesSumExact(tt, dif, h, nUp):
    s = 0.0
    pi2 = math.pi ** 2
    for n in range(1, nUp + 1):
        s += ((-1.0) ** n) * math.exp(-(n * n) * pi2 * tt * dif / (h * h)) / (n * n)
    return s

def q2VaporExact(tt, dif, h, cv, a1, kscg, nUp):
    return a1 * kscg * h * cv * ((tt * dif) / (h * h) - (1.0 / 6.0) - (2.0 / (math.pi ** 2)) * seriesSumExact(tt, dif, h, nUp))

def q2VaporSteady(tt, dif, h, cv, a1, kscg):
    return a1 * kscg * h * cv * (dif / (h * h)) * (tt - (h * h) / (6.0 * dif))

def fluxVaporExact(tt, dsc, hsc, cv, a1, kscg, nUp):
    base = a1 * kscg * hsc * cv * (dsc / (hsc * hsc))
    s = 0.0
    for n in range(1, nUp + 1):
        s += ((-1.0) ** n) * math.exp(-(n * n) * (math.pi ** 2) * tt * dsc / (hsc * hsc))
    return base * (1.0 + 2.0 * s)

def fluxVaporSteady(tt, tLag, dsc, hsc, cv, a1, kscg):
    base = a1 * kscg * hsc * cv * (dsc / (hsc * hsc))
    return base if tt > tLag else 0.0

def q2LiquidExact(tt, dif, h, cv, a1, kscw, nUp):
    return a1 * kscw * h * cv * ((tt * dif) / (h * h) - (1.0 / 6.0) - (2.0 / (math.pi ** 2)) * seriesSumExact(tt, dif, h, nUp))

def q2LiquidSteady(tt, dif, h, cv, a1, kscw):
    return a1 * kscw * h * cv * (dif / (h * h)) * (tt - (h * h) / (6.0 * dif))

def fluxLiquidExact(tt, dsc, hsc, cv, a1, kscw, nUp):
    base = a1 * kscw * hsc * cv * (dsc / (hsc * hsc))
    s = 0.0
    for n in range(1, nUp + 1):
        s += ((-1.0) ** n) * math.exp(-(n * n) * (math.pi ** 2) * tt * dsc / (hsc * hsc))
    return base * (1.0 + 2.0 * s)

def fluxLiquidSteady(tt, tLag, dsc, hsc, cv, a1, kscw):
    base = a1 * kscw * hsc * cv * (dsc / (hsc * hsc))
    return base if tt > tLag else 0.0

def findTimeToDose(targetDose, dif, h, cv, a1, k, nUp, x0=200.0, isVapor=True):
    if isVapor:
        f = lambda tt: q2VaporExact(tt, dif, h, cv, a1, k, nUp) - targetDose
    else:
        f = lambda tt: q2LiquidExact(tt, dif, h, cv, a1, k, nUp) - targetDose

    lo = 0.0
    hi = max(1.0, x0)
    fLo = f(lo)
    fHi = f(hi)
    tries = 0
    while fLo * fHi > 0.0 and tries < 40:
        hi *= 1.5
        fHi = f(hi)
        tries += 1

    if fLo * fHi <= 0.0:
        sol = optimize.root_scalar(f, bracket=(lo, hi), method="brentq")
        if sol.converged:
            return sol.root

    sol2 = optimize.root_scalar(f, x0=x0, method="newton")
    if sol2.converged and sol2.root >= 0.0:
        return sol2.root
    raise RuntimeError("Could not find a nonnegative root for time to reach dose.")

# ---------------------- Plotly figures ----------------------
def vline(x, yMin, yMax, name=None):
    return dict(type="line", x0=x, x1=x, y0=yMin, y1=yMax, line=dict(dash="dash"), name=name)

def hline(y, xMin, xMax, name=None):
    return dict(type="line", x0=xMin, x1=xMax, y0=y, y1=y, line=dict(dash="dash"), name=name)

def makePlotlyFigures(chemName, aeglTier, duration, qAllow, tLag, tReach, tReachL, p):
    # Time vectors
    t1 = np.linspace(0.0, max(tReach * 1.1, 1e-9), 500)
    t2 = np.linspace(0.0, max(tReachL * 1.2, 1e-9), 500)
    t3 = np.linspace(0.0, 10.0, 500)
    t4 = t3

    # Series values
    q1Exact = [q2VaporExact(t, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscg"], p["nUp"]) for t in t1]
    q1Steady = [q2VaporSteady(t, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscg"]) for t in t1]
    q2ExactVals = [q2LiquidExact(t, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscw"], p["nUp"]) for t in t2]
    q2SteadyVals = [q2LiquidSteady(t, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscw"]) for t in t2]
    f3Exact = [fluxVaporExact(t, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscg"], p["nUp"]) for t in t3]
    f3Steady = [fluxVaporSteady(t, tLag, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscg"]) for t in t3]
    f4Exact = [fluxLiquidExact(t, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscw"], p["nUp"]) for t in t4]
    f4Steady = [fluxLiquidSteady(t, tLag, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscw"]) for t in t4]

    # Figure 1: Vapor absorption
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=t1, y=q1Exact, mode="lines", name="Exact solution"))
    fig1.add_trace(go.Scatter(x=t1, y=q1Steady, mode="lines", name="Steady-state approx."))
    fig1.update_layout(
        title=f"Vapor Absorption — {chemName} (AEGL{aeglTier} {duration})",
        xaxis_title="t [h]",
        yaxis_title="Qa [mg]",
        shapes=[
            vline(tLag, min(q1Exact + q1Steady), max(q1Exact + q1Steady)),
            vline(tReach, min(q1Exact + q1Steady), max(q1Exact + q1Steady)),
            hline(qAllow, 0, float(max(t1)) if len(t1) else 0.0)
        ]
    )

    # Figure 2: Liquid absorption
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=t2, y=q2ExactVals, mode="lines", name="Exact solution"))
    fig2.add_trace(go.Scatter(x=t2, y=q2SteadyVals, mode="lines", name="Steady-state approx."))
    fig2.update_layout(
        title=f"Liquid Absorption — {chemName} (AEGL{aeglTier} {duration})",
        xaxis_title="t [h]",
        yaxis_title="Qa [mg]",
        shapes=[
            vline(tLag, min(q2ExactVals + q2SteadyVals), max(q2ExactVals + q2SteadyVals)),
            vline(tReachL, min(q2ExactVals + q2SteadyVals), max(q2ExactVals + q2SteadyVals)),
            hline(qAllow, 0, float(max(t2)) if len(t2) else 0.0)
        ]
    )

    # Figure 3: Vapor flux
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=t3, y=f3Exact, mode="lines", name="Exact flux"))
    fig3.add_trace(go.Scatter(x=t3, y=f3Steady, mode="lines", name="Steady-state flux"))
    fig3.update_layout(
        title=f"Vapor Flux — {chemName}",
        xaxis_title="t [h]",
        yaxis_title="Flux [mg/h]",
        shapes=[vline(tLag, min(f3Exact + f3Steady), max(f3Exact + f3Steady))]
    )

    # Figure 4: Liquid flux
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=t4, y=f4Exact, mode="lines", name="Exact flux"))
    fig4.add_trace(go.Scatter(x=t4, y=f4Steady, mode="lines", name="Steady-state flux"))
    fig4.update_layout(
        title=f"Liquid Flux — {chemName}",
        xaxis_title="t [h]",
        yaxis_title="Flux [mg/h]",
        shapes=[vline(tLag, min(f4Exact + f4Steady), max(f4Exact + f4Steady))]
    )

    # Return JSON strings
    return {
        "vaporAbsorption": fig1.to_json(),
        "liquidAbsorption": fig2.to_json(),
        "vaporFlux": fig3.to_json(),
        "liquidFlux": fig4.to_json()
    }

def run_aqueous_model(name):
    
    all_figs = {}
    durations = ["8hr", "4hr", "60min", "30min", "10min"]
    tiers = [1, 2, 3]

    for tier in tiers:
        for dur in durations:
            try:
                figs = run(name=name, aeglTier=tier, duration=dur)
                all_figs[f"AEGL{tier}_{dur}"] = figs
            except Exception as e:
                print(f"[SKIP] AEGL{tier}_{dur}: {e}")
                continue

    # Return flat dict with keys like AEGL1_8hr_vaporAbsorption
    merged = {}
    for key, figset in all_figs.items():
        for figName, figJson in figset.items():
            merged[f"{key}_{figName}"] = figJson

    return merged

# ---------------------- main runner (uses loader DB) ----------------------
def run(name=None, cas=None, aeglTier=1, duration="8hr", bodyWeightKg=70.0, exposedFraction=0.10, outdir=None):
    if not name and not cas:
        raise ValueError("Provide either --name or --cas.")

    row = getCompoundByName(name) if name else getCompoundByCas(cas)
    aegl = pickAegl(row, aeglTier, duration)  # mg/m^3
    p = initParamsFromRow(row, aegl, bodyWeightKg, exposedFraction)

    # breathing model & allowable dose
    breath = 2.10 * ((1000.0 * p["bw"]) ** (3.0 / 4.0)) * (10.0 ** -6.0) * 1440.0
    durMap = {"8hr": 8.0, "4hr": 4.0, "60min": 1.0, "30min": 0.5, "10min": 10.0/60.0}
    if duration not in durMap:
        raise ValueError("duration must be one of: 8hr, 4hr, 60min, 30min, 10min")
    tTox = durMap[duration]
    qAllow = aegl * breath * (tTox / 24.0)

    tLag = (p["h1"] ** 2) / (6.0 * p["dsc"])
    tReach = findTimeToDose(qAllow, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscg"], p["nUp"], x0=200.0, isVapor=True)
    tReachL = findTimeToDose(qAllow, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscw"], p["nUp"], x0=20.0, isVapor=False)

    figs = makePlotlyFigures(p["name"], aeglTier, duration, qAllow, tLag, tReach, tReachL, p)

    # Optional: save JSON files
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        for key, jsonStr in figs.items():
            outPath = os.path.join(outdir, f"{key}.json")
            with open(outPath, "w", encoding="utf-8") as f:
                f.write(jsonStr)
        print(f"Saved Plotly JSON to: {outdir}")

    # Minimal console debug summary
    vaporSteadyFlux  = p["a1"] * p["kscg"] * p["hsc"] * p["cv"] * p["dsc"] / (p["hsc"] ** 2)
    liquidSteadyFlux = p["a1"] * p["kscw"] * p["hsc"] * p["cv"] * p["dsc"] / (p["hsc"] ** 2)
    print("\n━━━━ Model Summary ━━━━")
    print(f"Name: {p['name']}  CAS: {p['cas']}")
    print(f"AEGL target: AEGL{aeglTier} {duration} = {aegl:.6g} mg/m^3")
    print(f"Qallow: {qAllow:.6g} mg | tLag: {tLag:.6g} h")
    print(f"tReach vapor: {tReach:.3g} h | tReach liquid: {tReachL:.3g} h")
    print(f"Flux_ss vapor: {vaporSteadyFlux:.3e} mg/h | Flux_ss liquid: {liquidSteadyFlux:.3e} mg/h")

    return figs

# ---------------------- CLI ----------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dermal absorption model → Plotly JSON (uses data_loader.py)")
    parser.add_argument("--name", help="Chemical Name (exact or case-insensitive match)")
    parser.add_argument("--cas", help="CAS number (exact match)")
    parser.add_argument("--aeglTier", type=int, default=1, choices=[1,2,3], help="AEGL tier (1/2/3)")
    parser.add_argument("--duration", default="8hr", choices=["8hr","4hr","60min","30min","10min"], help="AEGL duration")
    parser.add_argument("--bw", type=float, default=70.0, help="Body weight (kg)")
    parser.add_argument("--exposedFraction", type=float, default=0.10, help="Fraction of total skin area exposed (0-1)")
    parser.add_argument("--outdir", help="If provided, writes each figure JSON to this directory")
    args = parser.parse_args()

    run(
        name=args.name,
        cas=args.cas,
        aeglTier=args.aeglTier,
        duration=args.duration,
        bodyWeightKg=args.bw,
        exposedFraction=args.exposedFraction,
        outdir=args.outdir
    )
