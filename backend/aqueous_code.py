import math
import re
import argparse
import numpy as np
import pandas as pd
from scipy import optimize
import plotly.graph_objects as go
import os

from data_loader import compound_db, nameToCompound

def pickAegl(rowDict, aeglTier, duration):
    
    col = f"AEGL{aeglTier}_{duration}"
    if col not in rowDict:
        raise ValueError(f"AEGL column '{col}' not found in row.")
    val = rowDict[col]
    if pd.isna(val):
        raise ValueError(f"AEGL value missing for '{col}'.")
    return float(val)

def getCompoundByName(name):
    if name in nameToCompound:
        return nameToCompound[name]
    hit = compound_db[compound_db["Name"].str.strip().str.lower() == str(name).strip().lower()]
    if hit.empty:
        raise ValueError(f"Chemical with Name='{name}' not found in database.")
    return hit.iloc[0].to_dict()

def getCompoundByCas(cas):
    hit = compound_db[compound_db["CAS"].astype(str).str.strip() == str(cas).strip()]
    if hit.empty:
        raise ValueError(f"Chemical with CAS='{cas}' not found in database.")
    return hit.iloc[0].to_dict()

AEGL_COL_RE = re.compile(r"^AEGL([123])_(8hr|4hr|60min|30min|10min)$")

def list_available_aegl_targets(rowDict):
   
    targets = []
    for key, val in rowDict.items():
        m = AEGL_COL_RE.match(str(key))
        if not m:
            continue
        if pd.isna(val):
            continue
        tier = int(m.group(1))
        duration = m.group(2)
        targets.append((tier, duration))
    order = {"8hr": 0, "4hr": 1, "60min": 2, "30min": 3, "10min": 4}
    targets.sort(key=lambda td: (td[0], order.get(td[1], 99)))
    return targets

def initParamsFromRow(row, aeglMgPerM3, bodyWeightKg=70.0, exposedFraction=0.10):
   
    mw = float(row["MW"])
    logKow = float(row["logP"])
    kow = 10 ** logKow

    kscw = 0.04 * (kow ** 0.81) + 4.06 * (kow ** 0.27) + 0.359

    concComptox = float(aeglMgPerM3) 
    csPpm = concComptox * 24.45 / mw    
    cv = (10 ** -6) * concComptox     

    hsc = 10 * 0.0001                  
    h1 = hsc
    logPscw = -2.8 + (0.66 * logKow) - (0.0056 * mw)
    pscw = 10 ** logPscw                
    dsc = pscw * h1 / kscw             

    r = 0.0821
    t = 298.15
    H = row.get("henryConstant")
    if H is not None and pd.notna(H) and float(H) > 0.0:
        H = float(H)                    
        hcp = (1.0 / H) / 1000.0       
        kwg = hcp * r * t               
    else:
        hcp = 1.0 / 1000.0
        kwg = hcp * r * t

    kscg = kscw * kwg                   

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

def vline(x, yMin, yMax, name=None):
    return dict(type="line", x0=x, x1=x, y0=yMin, y1=yMax, line=dict(dash="dash"), name=name)

def hline(y, xMin, xMax, name=None):
    return dict(type="line", x0=xMin, x1=xMax, y0=y, y1=y, line=dict(dash="dash"), name=name)

def makePlotlyFigures(chemName, aeglTier, duration, qAllow, tLag, tReach, tReachL, p):
    import numpy as np
    import plotly.graph_objects as go

    t1 = np.linspace(0.0, max(tReach * 1.1, 1e-9), 500)
    t2 = np.linspace(0.0, max(tReachL * 1.2, 1e-9), 500)
    t3 = np.linspace(0.0, 10.0, 500)
    t4 = t3

    q1Exact = [q2VaporExact(t, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscg"], p["nUp"]) for t in t1]
    q1Steady = [q2VaporSteady(t, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscg"]) for t in t1]
    q2ExactVals = [q2LiquidExact(t, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscw"], p["nUp"]) for t in t2]
    q2SteadyVals = [q2LiquidSteady(t, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscw"]) for t in t2]
    f3Exact = [fluxVaporExact(t, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscg"], p["nUp"]) for t in t3]
    f3Steady = [fluxVaporSteady(t, tLag, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscg"]) for t in t3]
    f4Exact = [fluxLiquidExact(t, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscw"], p["nUp"]) for t in t4]
    f4Steady = [fluxLiquidSteady(t, tLag, p["dsc"], p["hsc"], p["cv"], p["a1"], p["kscw"]) for t in t4]

    legend_style = dict(
        orientation="h",
        x=0.5,
        y=-0.3,
        xanchor="center",
        yanchor="top",
        font=dict(size=12)
    )
    margin_style = dict(t=50, b=120)

    # ----- Graph 1: Vapor Absorption -----
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=t1, y=q1Exact, mode="lines", name="Exact solution", line=dict(color="royalblue")))
    fig1.add_trace(go.Scatter(
        x=t1, y=q1Steady, mode="lines", name="Steady-state approx.",
        line=dict(color="orangered", dash="dash", width=2)
    ))
    fig1.update_layout(
        title=f"Vapor Absorption — {chemName} (AEGL{aeglTier} {duration})",
        xaxis_title="t [h]",
        yaxis_title="Qa [mg]",
        legend=legend_style,
        margin=margin_style,
        # width=600,
        # height=420,
        shapes=[
            vline(tLag, min(q1Exact + q1Steady), max(q1Exact + q1Steady)),
            vline(tReach, min(q1Exact + q1Steady), max(q1Exact + q1Steady)),
            hline(qAllow, 0, float(max(t1)))
        ]
    )

    # ----- Graph 2: Liquid Absorption -----
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=t2, y=q2ExactVals, mode="lines", name="Exact solution", line=dict(color="royalblue")))
    fig2.add_trace(go.Scatter(
        x=t2, y=q2SteadyVals, mode="lines", name="Steady-state approx.",
        line=dict(color="orangered", dash="dash", width=2)
    ))
    fig2.update_layout(
        title=f"Liquid Absorption — {chemName} (AEGL{aeglTier} {duration})",
        xaxis_title="t [h]",
        yaxis_title="Qa [mg]",
        legend=legend_style,
        margin=margin_style,
        # width=600,
        # height=420,
        shapes=[
            vline(tLag, min(q2ExactVals + q2SteadyVals), max(q2ExactVals + q2SteadyVals)),
            vline(tReachL, min(q2ExactVals + q2SteadyVals), max(q2ExactVals + q2SteadyVals)),
            hline(qAllow, 0, float(max(t2)))
        ]
    )

    # ----- Graph 3: Vapor Flux -----
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=t3, y=f3Exact, mode="lines", name="Exact flux", line=dict(color="royalblue")))
    fig3.add_trace(go.Scatter(x=t3, y=f3Steady, mode="lines", name="Steady-state flux", line=dict(color="orangered")))
    fig3.update_layout(
        title=f"Vapor Flux — {chemName} (AEGL{aeglTier} {duration})",
        xaxis_title="t [h]",
        yaxis_title="Flux [mg/h]",
        legend=legend_style,
        margin=margin_style,
        # width=600,
        # height=420,
        shapes=[
            vline(tLag, min(f3Exact + f3Steady), max(f3Exact + f3Steady))
        ]
    )

    # ----- Graph 4: Liquid Flux -----
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=t4, y=f4Exact, mode="lines", name="Exact flux", line=dict(color="royalblue")))
    fig4.add_trace(go.Scatter(x=t4, y=f4Steady, mode="lines", name="Steady-state flux", line=dict(color="orangered")))
    fig4.update_layout(
        title=f"Liquid Flux — {chemName} (AEGL{aeglTier} {duration})",
        xaxis_title="t [h]",
        yaxis_title="Flux [mg/h]",
        legend=legend_style,
        margin=margin_style,
        # width=600,
        # height=420,
        shapes=[
            vline(tLag, min(f4Exact + f4Steady), max(f4Exact + f4Steady))
        ]
    )

    return {
        "vaporAbsorption": fig1.to_json(),
        "liquidAbsorption": fig2.to_json(),
        "vaporFlux": fig3.to_json(),
        "liquidFlux": fig4.to_json()
    }

def _run_single_from_row(row, aeglTier, duration, bodyWeightKg, exposedFraction):
    aegl = pickAegl(row, aeglTier, duration)
    p = initParamsFromRow(row, aegl, bodyWeightKg, exposedFraction)

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

    vaporSteadyFlux  = p["a1"] * p["kscg"] * p["hsc"] * p["cv"] * p["dsc"] / (p["hsc"] ** 2)
    liquidSteadyFlux = p["a1"] * p["kscw"] * p["hsc"] * p["cv"] * p["dsc"] / (p["hsc"] ** 2)
    print("\n━━━━ Model Summary ━━━━")
    print(f"Name: {p['name']}  CAS: {p['cas']}")
    print(f"AEGL target: AEGL{aeglTier} {duration} = {aegl:.6g} mg/m^3")
    print(f"Qallow: {qAllow:.6g} mg | tLag: {tLag:.6g} h")
    print(f"tReach vapor: {tReach:.3g} h | tReach liquid: {tReachL:.3g} h")
    print(f"Flux_ss vapor: {vaporSteadyFlux:.3e} mg/h | Flux_ss liquid: {liquidSteadyFlux:.3e} mg/h")

    return figs

def run_all_aegl(name=None, cas=None, bodyWeightKg=70.0, exposedFraction=0.10, outdir=None):

    if not name and not cas:
        raise ValueError("Provide either --name or --cas.")
    row = getCompoundByName(name) if name else getCompoundByCas(cas)

    available = list_available_aegl_targets(row)
    if not available:
        raise ValueError("No AEGL targets available for this chemical (all missing/NaN).")

    merged = {}
    for tier, dur in available:
        try:
            figset = _run_single_from_row(row, tier, dur, bodyWeightKg, exposedFraction)
        except Exception as e:
            print(f"[SKIP] AEGL{tier}_{dur}: {e}")
            continue

        for figName, figJson in figset.items():
            merged[f"AEGL{tier}_{dur}_{figName}"] = figJson

    if outdir:
        os.makedirs(outdir, exist_ok=True)
        for key, jsonStr in merged.items():
            outPath = os.path.join(outdir, f"{key}.json")
            with open(outPath, "w", encoding="utf-8") as f:
                f.write(jsonStr)
        print(f"Saved Plotly JSON to: {outdir}")

    return merged

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dermal absorption model → Plotly JSON (uses data_loader.py)")
    parser.add_argument("--name", help="Chemical Name (exact or case-insensitive match)")
    parser.add_argument("--cas", help="CAS number (exact match)")
    parser.add_argument("--aeglTier", type=int, choices=[1,2,3], help="AEGL tier (1/2/3)")
    parser.add_argument("--duration", choices=["8hr","4hr","60min","30min","10min"], help="AEGL duration")
    parser.add_argument("--all", action="store_true", help="Compute for all available AEGL targets on this chemical")
    parser.add_argument("--bw", type=float, default=70.0, help="Body weight (kg)")
    parser.add_argument("--exposedFraction", type=float, default=0.10, help="Fraction of total skin area exposed (0-1)")
    parser.add_argument("--outdir", help="If provided, writes each figure JSON to this directory")
    args = parser.parse_args()

    if args.all:
        _ = run_all_aegl(
            name=args.name,
            cas=args.cas,
            bodyWeightKg=args.bw,
            exposedFraction=args.exposedFraction,
            outdir=args.outdir
        )
    else:
        if args.aeglTier is None or args.duration is None:
            raise SystemExit("AEGL Tier and Time not mentioned")
        _ = run(
            name=args.name,
            cas=args.cas,
            aeglTier=args.aeglTier,
            duration=args.duration,
            bodyWeightKg=args.bw,
            exposedFraction=args.exposedFraction,
            outdir=args.outdir
        )
