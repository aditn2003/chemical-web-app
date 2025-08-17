import math
import re
import os
import numpy as np
from collections import OrderedDict
from scipy.optimize import newton
import pandas as pd
import matplotlib
from IPython.display import clear_output
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
from pubchem_utils import safe_mol_from_smiles, build_compound
from data_loader import compound_db

# === Reactivity Scoring Factors ===
class_reactivity_factors = {
    "Nerve agent": 1.0,
    "Blister agent": 0.4,
    "Nitroaromatic": 0.05,
    "Aromatic hydrocarbon": 0.001,
    "Alcohol": 0.001,
    "Ketone": 0.002,
    "Other": 0.001
}

def analyze_reactivity(compound):
    smiles = compound.get("SMILES")
    mol = safe_mol_from_smiles(smiles, compound.get("Name", "unknown")) if smiles else None
    cls = compound.get("class", "Other")
    MW = float(compound.get("MW", 0))
    reactive_score = class_reactivity_factors.get(cls, 0.001)
    reactive_groups = []
    oxime_reactivity = "Negligible"

    if mol:
        from rdkit import Chem
        patterns = {
            "Alkene": "[C;!R]=[C;!R]",
            "Carbonyl": "C=O",
            "Nitro": "[N+](=O)[O-]",
            "Thiol": "[SH]",
            "Amine": "[NX3;H2,H1;!$(NC=O)]",
            "Phenol": "c1ccc(cc1)O",
            "Phosphate ester": "P(=O)(O)(O)",
            "Organophosphorus": "P(=O)(O)(C)"
        }
        for label, smarts in patterns.items():
            if mol.HasSubstructMatch(Chem.MolFromSmarts(smarts)):
                reactive_groups.append(label)

        if "Organophosphorus" in reactive_groups:
            oxime_reactivity = "High"
        elif "Carbonyl" in reactive_groups or "Nitro" in reactive_groups:
            oxime_reactivity = "Moderate"

        if mol.HasSubstructMatch(Chem.MolFromSmarts("[F-]")) or mol.HasSubstructMatch(Chem.MolFromSmarts("F")):
            leaving_group = "F"
        elif mol.HasSubstructMatch(Chem.MolFromSmarts("Cl")):
            leaving_group = "Cl"
        elif mol.HasSubstructMatch(Chem.MolFromSmarts("Br")):
            leaving_group = "Br"
        elif mol.HasSubstructMatch(Chem.MolFromSmarts("C#N")):
            leaving_group = "CN"
        elif mol.HasSubstructMatch(Chem.MolFromSmarts("[S]")):
            leaving_group = "S"
        else:
            leaving_group = "Other"
    else:
        leaving_group = "Other"

    steric = "Low" if MW <= 150 else "Medium" if MW <= 300 else "High"

    return {
        "reactiveGroups": reactive_groups,
        "leavingGroup": leaving_group,
        "steric": steric,
        "reactiveScore": reactive_score,
        "chemicalClass": cls,
        "oximeReactivity": oxime_reactivity
    }

def predict_kr(compound):
    reactivity = analyze_reactivity(compound)
    MW = float(compound.get("MW", 100))
    logP = float(compound.get("logP") or 0.3)

    baseKr = {
        "Cl": 0.1,
        "Br": 0.2,
        "F": 0.05,
        "CN": 0.01,
        "S": 0.005
    }.get(reactivity["leavingGroup"], 0.001 * reactivity["reactiveScore"])

    logP_penalty = math.exp(-1.0 * abs(logP - 0.3))
    mw_penalty = math.exp(-0.002 * abs(MW - 140))
    steric_factor = {"Low": 1.0, "Medium": 0.7, "High": 0.4}
    steric_adj = steric_factor.get(reactivity["steric"], 1.0)

    finalKr = baseKr * logP_penalty * mw_penalty * steric_adj

    if compound.get("class") not in ["Nerve agent", "Blister agent"]:
        finalKr = min(finalKr, 0.005)

    return {
        "compound": compound.get("Name", "Unknown"),
        "predicted_kr": max(min(finalKr, 10.0), 0.00001),
        "confidence": "High" if compound.get("class") == "Nerve agent" else "Low"
    }


def getAvailableAeglTimes(compound: dict) -> list[str]:

    times = []
    for key in compound.keys():
        match = re.match(r'AEGL\d+_(.+)', key)
        if match:
            times.append(match.group(1))

    uniqueTimes = list(OrderedDict.fromkeys(times))
    return uniqueTimes

def timeStringToHours(timeStr: str) -> float:

    timeMap = {
        "8hr":   8,
        "4hr":   4,
        "60min": 1,
        "30min": 0.5,
        "10min": 1 / 6,
    }

    return timeMap.get(timeStr, 8)

def generateAeglGraphs(times, doseList, fluxList):
    graph1 = go.Figure()
    graph1.add_trace(go.Scatter(x=times, y=doseList, mode="lines+markers", name="Dose"))
    graph1.update_layout(
        title="Dose Absorbed vs. Exposure Time",
        xaxis_title="Time (min)",
        yaxis_title="Dose (mg/kg)",
        template="plotly_white"
    )

    graph3 = go.Figure()
    graph3.add_trace(go.Scatter(x=times, y=fluxList, mode="lines+markers", name="Flux"))
    graph3.update_layout(
        title="Skin Flux vs. Exposure Time",
        xaxis_title="Time (min)",
        yaxis_title="Flux (mg/cm²/min)",
        template="plotly_white"
    )

    return graph1.to_dict(), graph3.to_dict()

def getAeglValue(compound: dict, level: int, timeStr: str, verbose=False) -> float | str:
    key = f"AEGL{level}_{timeStr}"

    # if verbose:
    #     print(f"DEBUG: Looking for key '{key}' in compound {compound.get('name')}")

    if key in compound:
        value = compound[key]

        # if verbose:
        #     print(f"DEBUG: Found {key} = {value}")

        if isinstance(value, (int, float)) and value > 0:
            return value
        else:
            # if verbose:
            #     print(f"DEBUG: Value '{value}' is not a valid number (undefined/zero/negative)")
            return "NotAvailable"
    else:
        # if verbose:
        #     print(f"DEBUG: Key '{key}' NOT FOUND")
        return "NotAvailable"

def analyzeSingleAegl(compound: dict, aeglLevel: int, timeStr: str, verbose=False):
    # if verbose:
    #     print(f"DEBUG: Requesting AEGL {aeglLevel} for time {timeStr}")
    aegl = getAeglValue(compound, aeglLevel, timeStr)
    # if verbose:
    #     print(f"DEBUG: Retrieved AEGL value = {aegl}")

    if aegl == "NotAvailable":
        # if verbose:
        #     print(f"AEGL{aeglLevel} for {timeStr} not available for {compound.get('name')}")
        return "NotAvailable"

    molecularWeight = compound["MW"]
    logKow = compound.get("logKow")

# Fallback if only logP is available
    if logKow is None and "logP" in compound:
        logKow = compound["logP"]
    henryConstant = compound["henryConstant"]
    vaporPressure = compound["vaporPressure"]
    waterSolubility = compound["solubility"] / 1000

    # Fixed parameters
    bodyWeight = 70
    hsc = 10 * 0.0001
    h1 = hsc
    gasConstant = 0.0821
    temperature = 298.15
    nup = 10
    a1 = 0.1 * 18150
    ttox = timeStringToHours(timeStr)

    # Derived parameters
    kow = 10 ** logKow
    kscw = 0.04 * kow ** 0.81 + 4.06 * kow ** 0.27 + 0.359
    concCompTox = aegl
    csPpm = concCompTox * 24.45 / molecularWeight
    cv = 1e-6 * concCompTox
    logPscw = -2.8 + (0.66 * logKow) - (0.0056 * molecularWeight)
    pscw = 10 ** logPscw
    dsc = (pscw * h1) / kscw
    hcp = (1 / henryConstant) / 1000
    kwg = hcp * gasConstant * temperature
    kscg = kscw * kwg

    breath = 2.10 * (1000 * bodyWeight) ** (3 / 4) * 1e-6 * (1440 / 1)
    qallow = aegl * breath * (ttox / 24)

    tlag = h1 ** 2 / (6 * dsc)
    if verbose:
        # print(f"DEBUG PARAMETERS for AEGL{aeglLevel} ({timeStr}):")
        print(f" AEGL = {aegl:.6f} mg/m³")
        print(f" Cv (skin concentration) = {cv:.4e} mg/mL")
        print(f" Qallow (allowable dose) = {qallow:.4e} mg")

    steadyStateFlux = a1 * kscg * hsc * cv * dsc / (hsc ** 2)
    if verbose:
        print(f" Steady-state flux = {steadyStateFlux:.4e} mg/hr")

    theoreticalTime = qallow / steadyStateFlux + tlag
    if verbose:
        print(f" Theoretical time (steady-state) = {theoreticalTime:.4f} hours")
        print(f" Ratio (Qallow/flux) = {qallow / steadyStateFlux:.4f} hours\n")

    machineEps = np.finfo(float).eps
    pi = np.pi

    def q2(t, dif, h, cs, nup):
        summation = 0.0
        for n in range(1, nup + 1):
            term = (-1) ** n * np.exp(-n**2 * pi**2 * t * dif / h**2) / n**2
            if abs(term) > machineEps:
                summation += term
        return a1 * kscg * h * cv * (t * dif / h**2 - 1 / 6 - 2 / pi**2 * summation)

    def q2n(t, dif, h, cs, nup):
        return a1 * kscg * h * cv * dif / h**2 * (t - h**2 / (6 * dif))

    def fluxExact(t):
        return a1 * kscg * hsc * cv * dsc / (hsc**2) * (1 + 2 * sum((-1) ** n * np.exp(-n**2 * pi**2 * t * dsc / hsc**2) for n in range(1, nup + 1)))

    def fluxSteadyState(t):
        return a1 * kscg * hsc * cv * dsc / (hsc**2) if t > tlag else 0.0

    # if verbose:
        # print(f"DEBUG: About to calculate tReach for AEGL{aeglLevel} with Qallow = {qallow:.4e}")

    try:
        timeToReachDose = newton(lambda t: q2(t, dsc, hsc, cv, nup) - qallow, 100.0)
        tReach = timeToReachDose if isinstance(timeToReachDose, (int, float)) and timeToReachDose > 0 else None
        # if verbose:
        #     if tReach:
        #         print(f"DEBUG: Calculated tReach = {tReach:.4f} for AEGL{aeglLevel}")
        #     else:
        #         print(f"DEBUG: tReach is not a valid positive number → {timeToReachDose}")
    except (RuntimeError, OverflowError) as err:
        # if verbose:
        #     print(f"DEBUG: Root-finding failed: {err}")
        tReach = None

    if tReach is not None:
        verification = q2(tReach, dsc, hsc, cv, nup)
        # if verbose:
        #     print(f"DEBUG: Verification - Q2({tReach:.4f}) = {verification:.4e}, target was {qallow:.4e}")
    else:
        # if verbose:
        #     print(f"DEBUG: FindRoot FAILED for AEGL{aeglLevel}")
        tReach = "FindRootFailed"

       # === Plotly graph generation (replaces Matplotlib) ===
    absorptionGraphJson = None
    fluxGraphJson = None

    if isinstance(tReach, (int, float)) and tReach > 0:
        tAxis = np.linspace(0, tReach * 1.1, 500)
        exactDose = [q2(tVal, dsc, hsc, cv, nup) for tVal in tAxis]
        steadyDose = [q2n(tVal, dsc, hsc, cv, nup) for tVal in tAxis]

        # Absorption (Qa vs time)
        fig_abs = go.Figure()
        fig_abs.add_trace(go.Scatter(x=tAxis, y=exactDose, mode="lines", name="Exact"))
        fig_abs.add_trace(go.Scatter(x=tAxis, y=steadyDose, mode="lines", name="Steady-state", line=dict(dash="dash")))
        fig_abs.add_vline(x=tlag, line=dict(dash="dash", width=1, color="gray"))
        fig_abs.add_vline(x=tReach, line=dict(dash="dash", width=1, color="gray"))
        fig_abs.add_hline(y=qallow, line=dict(dash="dash", width=1, color="gray"))
        fig_abs.update_layout(
            title=f"{compound['Name']} – AEGL{aeglLevel} ({timeStr}): Absorption",
            xaxis_title="t [h]",
            yaxis_title="Qa [mg]",
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
        )
        absorptionGraphJson = pio.to_json(fig_abs)

        # Flux (Flux vs time)
       # Flux (Flux vs time) — styled to match purple shaded Matplotlib version
        tAxisFlux = np.linspace(0, 10, 500)
        exactFlux = [fluxExact(tVal) for tVal in tAxisFlux]
        steadyFlux = [fluxSteadyState(tVal) for tVal in tAxisFlux]

        fig_flux = go.Figure()

# Area under the curve: purple fill
        fig_flux.add_trace(go.Scatter(
            x=tAxisFlux, y=exactFlux,
            mode="lines",
            name="Exact flux",
            line=dict(color="purple", width=3),
            fill="tozeroy",
            fillcolor="rgba(128,0,128,0.2)"  # semi-transparent purple
        ))

    # Steady-state horizontal line
        fig_flux.add_trace(go.Scatter(
            x=tAxisFlux,
            y=steadyFlux,
            mode="lines",
            name="Steady-state flux",
            line=dict(color="green", width=3, dash="dash")
        ))

    # Add vertical dashed line at tlag
        fig_flux.add_vline(
            x=tlag,
            line=dict(dash="dash", width=1.5, color="gray"),
            annotation_text="tlag",
            annotation_position="top left"
        )

        fig_flux.update_layout(
            title=f"{compound['Name']} – AEGL{aeglLevel} ({timeStr}): Flux",
            xaxis_title="t [h]",
            yaxis_title="Flux [mg/h]",
            template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
        )
        fluxGraphJson = pio.to_json(fig_flux)

    else:
        fig_abs = go.Figure().add_annotation(text="tReach calculation failed", showarrow=False)
        fig_abs.update_layout(template="plotly_white")
        absorptionGraphJson = pio.to_json(fig_abs)

        fig_flux = go.Figure().add_annotation(text="tReach calculation failed", showarrow=False)
        fig_flux.update_layout(template="plotly_white")
        fluxGraphJson = pio.to_json(fig_flux)


    return {
        "compound": compound["Name"],
        "cas": compound["CAS"],
        "mw": molecularWeight,
        "logKow": logKow,
        "aegl": aegl,
        "aeglLevel": aeglLevel,
        "timeStr": timeStr,
        "exposureTimeHours": ttox,
        "pscw": pscw,
        "dsc": dsc,
        "tlag": tlag,
        "kscw": kscw,
        "kscg": kscg,
        "cv": cv,
        "qallow": qallow,
        "tReach": tReach,
        "steadyStateFlux": steadyStateFlux,
        "absorptionGraph": absorptionGraphJson,
        "fluxGraph": fluxGraphJson
    }

# Testing above function(WORKS) -
# result = analyzeSingleAegl(nameToCompound["Sarin"], 1, "8hr")
# print("AEGL value:", result["aegl"])
# print("tReach:", result["tReach"])

# Function to analyze all AEGL levels for a compound
def analyzeAllAegls(compound: dict, selectedTimes=None, verbose=False):
    availableTimes = getAvailableAeglTimes(compound)

    # Handle the case where selectedTimes might be a nested list or empty
    if selectedTimes is None:
        timesToAnalyze = availableTimes
    elif isinstance(selectedTimes, list) and len(selectedTimes) > 0:
        flattened = []
        for item in selectedTimes:
            if isinstance(item, list):
                flattened.extend(item)
            else:
                flattened.append(item)
        timesToAnalyze = flattened
    else:
        timesToAnalyze = []

    timesToAnalyze = list(set(timesToAnalyze) & set(availableTimes))

    if verbose:
        print(f"Analyzing compound: {compound['Name']} {compound.get('CAS', '')}")
        print("Available AEGL times:", availableTimes)
        print("Selected times input:", selectedTimes)
        print("Times to analyze:", timesToAnalyze)
        print("═" * 70)

    allResults = []

    if len(timesToAnalyze) > 0:
        for level in range(1, 4):
            for timeStr in timesToAnalyze:
                result = analyzeSingleAegl(compound, level, timeStr, verbose=verbose)

                if result != "NotAvailable":
                    allResults.append(result)

                    # logic always runs
                    tReach = result["tReach"]
                    expectedTime = result["qallow"] / result["steadyStateFlux"] + result["tlag"]

                    if verbose:
                        print(f"\n\033[1mAEGL{level} ({timeStr})\033[0m")
                        print(f"AEGL value: {result['aegl']:.4f} mg/m³")
                        print(f"Exposure time: {result['exposureTimeHours']:.3f} hours")
                        print(f"Allowable dose: {result['qallow']:.4f} mg")
                        print(f"Lag time: {result['tlag']:.3f} hours")
                        print(f"Steady-state flux: {result['steadyStateFlux']:.3e} mg/hr")

                    if tReach in [None, "FindRootFailed"]:
                        if verbose:
                            print("\033[91mTime to reach allowable dose: CALCULATION FAILED\033[0m")
                    else:
                        if verbose:
                            print(
                                f"Time to reach allowable dose: {tReach:.3f} hours "
                                f"({tReach / 24:.3f} days)"
                            )

                    if verbose:
                        print(f"Expected time (steady-state approx): {expectedTime:.3f} hours\n")
                        # display(result["graph1"])
                        # display(result["graph3"])
                        print("\n" * 2)

    return allResults


def createSummaryTable(results: list[dict]) -> pd.DataFrame:
    summaryData = []

    for result in results:
        tReach = result["tReach"]
        tReachHr = tReach if isinstance(tReach, (int, float)) else None
        tReachDay = tReachHr / 24 if tReachHr is not None else None

        row = {
            "Compound": result["compound"],
            "CAS": result["cas"],
            "AEGL Type": f"AEGL{result['aeglLevel']} ({result['timeStr']})",
            "MW (g/mol)": round(result["mw"], 2),
            "LogKow": round(result["logKow"], 2),
            "AEGL (mg/m³)": f"{result['aegl']:.2e}",
            "Lag Time (hr)": round(result["tlag"], 2),
            "Time to Dose (hr)": round(tReachHr, 1) if tReachHr is not None else "—",
            "Time to Dose (days)": round(tReachDay, 2) if tReachDay is not None else "—"
        }

        summaryData.append(row)

    df = pd.DataFrame(summaryData)
    return df


def analyzeAllCompounds(compoundData: list[dict], selectedTimes=None, verbose=False): 
    allResults = []

    if verbose:
        print("BATCH ANALYSIS OF ALL COMPOUNDS")
        print("═" * 70)

    for compound in compoundData:
        compoundResults = analyzeAllAegls(compound, selectedTimes, verbose=verbose)
        if compoundResults:
            allResults.extend(compoundResults)

        if verbose:
            print("\n" + "-" * 60 + "\n")

    # Summary Table (always created and exported)
    summaryTable = createSummaryTable(allResults)

    if verbose:
        print("SUMMARY TABLE FOR ALL ANALYSES")
        print("═" * 70)
        #display(summaryTable)

    summaryTable.to_csv("aegl_results.csv", index=False)

    print("\n AEGL results saved as 'aegl_results.csv'.")

    return allResults

# === Display analysis for one compound ===
def quick_predict_exact(name):
    compound = build_compound(name)
    clear_output()
    if compound is None:
        print(f"Compound '{name}' could not be retrieved.")
        return

    reactivity = analyze_reactivity(compound)
    result = predict_kr(compound)

    print("\n" + "═" * 70)
    print("CHEMICAL REACTIVITY ANALYSIS RESULTS")
    print("═" * 70 + "\n")
    print(f"Compound: {compound['Name']}")
    print(f"Predicted kr: {result['predicted_kr']:.6f} M⁻¹·min⁻¹\n")

    print("TECHNICAL DETAILS")
    print(f"Chemical Formula: {compound.get('formula', 'N/A')}")
    print(f"Molecular Weight: {compound.get('MW', 'N/A')} g/mol")
    print(f"LogP: {compound.get('logP', 'N/A')}")
    print(f"Classification: {reactivity['chemicalClass']}")
    print(f"Oxime Target Reactivity: {reactivity['oximeReactivity']}\n")

    print("REACTIVITY ANALYSIS")
    print(f"Reactive Groups: {', '.join(reactivity['reactiveGroups']) or 'None detected'}")
    print(f"Leaving Group: {reactivity['leavingGroup']}")
    print(f"Steric Hindrance: {reactivity['steric']}")
    print(f"Base Score: {reactivity['reactiveScore']}")
    print("\nAnalysis complete for:", compound["Name"])

    print("\n" + "═" * 70)
    print("AEGL ANALYSIS")
    print("═" * 70)

    selectedTimes = ["8hr", "4hr", "60min", "30min", "10min"]
    aeglResults = analyzeAllAegls(compound, selectedTimes, verbose=True)

    if not aeglResults:
        print("No AEGL data available or analysis failed.")

# ========================================= Backend Functions Start ==========================================

# converts np.float64 -> float, etc.
def makeJsonSafe(obj):
    if isinstance(obj, dict):
        return {k: makeJsonSafe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [makeJsonSafe(v) for v in obj]
    elif isinstance(obj, np.generic):
        return obj.item()
    else:
        return obj
    

_global_scatter_cache = {
    "json": None,
    "last_modified": None
}

# Graph for all chemcial types and their k values
def getGlobalScatterGraph():

    global _global_scatter_cache

    csv_path = "Database/combined_chemicals.csv"  

    try:
        last_modified = os.path.getmtime(csv_path)

        if (_global_scatter_cache["json"] is not None
            and _global_scatter_cache["last_modified"] == last_modified):
            return _global_scatter_cache["json"]

        rows = []
        for _, row in compound_db.iterrows():
            comp = row.to_dict()
            pred = predict_kr(comp)
            rows.append({
                "Name": comp.get("Name", "Unknown"),
                "Class": comp.get("class", "Other"),
                "Predicted_kr": pred["predicted_kr"],
            })

        df = pd.DataFrame(rows)

        fig = px.scatter(
            df,
            x="Class",
            y="Predicted_kr",
            color="Class",
            hover_name="Name",
            log_y=True,
            title="Predicted kr by Compound Class (All Compounds)",
            template="plotly_white"
        )
        fig.update_traces(marker=dict(opacity=0.7, line=dict(width=0.5, color='DarkSlateGrey')))
        fig.update_layout(
            height=500,
            showlegend=False,
            xaxis_title="Chemical Class",
            yaxis_title="kr (M⁻¹·min⁻¹)"
        )

        graph_json = pio.to_json(fig)

        _global_scatter_cache["json"] = graph_json
        _global_scatter_cache["last_modified"] = last_modified

        return graph_json

    except Exception as e:
        return pio.to_json(px.scatter(title=f"Error generating scatter: {e}"))

# Function for the final combined result with k prediction and AEGL
def generateCombinedSummaryCsv(
    krCsvPath="kr_predictions_135.csv",
    aeglCsvPath="aegl_results.csv",
    masterCsvPath="Database/cleaned_chemicals_data.csv",
    outputCsvPath="combined_summary_per_compound.csv",
    verbose=False
):
    kr_df = pd.read_csv(krCsvPath)
    aegl_df = pd.read_csv(aeglCsvPath)
    master_df = pd.read_csv(masterCsvPath)

    kr_df.columns = kr_df.columns.str.strip().str.lower()
    aegl_df.columns = aegl_df.columns.str.strip().str.lower()
    master_df.columns = master_df.columns.str.strip().str.lower()

    if "name" not in master_df.columns:
        raise ValueError(f"'Name' column not found in master CSV. Available: {list(master_df.columns)}")

    kr_df["name"] = kr_df["name"].astype(str).str.strip().str.lower()
    master_df["name"] = master_df["name"].astype(str).str.strip().str.lower()

    kr_df = pd.merge(kr_df, master_df[["name", "cas"]], on="name", how="left")
    kr_df = kr_df.rename(columns={"name": "Compound"})  # this is now lowercase strings

    pivot_fields = ["aegl (mg/m³)", "lag time (hr)", "time to dose (hr)", "time to dose (days)"]
    pivoted = []
    for field in pivot_fields:
        if field in aegl_df.columns:
            p = aegl_df.pivot(index="compound", columns="aegl type", values=field)
            p.columns = [f"{col} - {field}" for col in p.columns]
            pivoted.append(p)
    aegl_wide = pd.concat(pivoted, axis=1).reset_index() if pivoted else pd.DataFrame(columns=["compound"])

    logkow_df = aegl_df[["compound", "logkow"]].drop_duplicates().reset_index(drop=True)
    aegl_summary = pd.merge(logkow_df, aegl_wide, on="compound", how="outer")

    aegl_summary = aegl_summary.rename(columns={"compound": "Compound"})
    aegl_summary["Compound"] = aegl_summary["Compound"].astype(str).str.strip().str.lower()

    final = pd.merge(kr_df, aegl_summary, on="Compound", how="outer")

    final["Compound"] = final["Compound"].str.title()

    final = final.fillna("undefined")

    def is_aegl_col(c: str) -> bool:
        cl = c.lower()
        return ("aegl (" in cl or "lag time (hr)" in cl or
                "time to dose (hr)" in cl or "time to dose (days)" in cl or "aegl " in cl)

    priority = ["Compound", "cas", "Class", "MW", "LogP", "Predicted_kr",
                "ReactiveGroups", "LeavingGroup", "Steric", "BaseScore", "LogKow"]
    cols = list(final.columns)
    first = [c for c in priority if c in cols]
    non_aegl_rest = [c for c in cols if c not in first and not is_aegl_col(c)]
    aegl_cols = [c for c in cols if is_aegl_col(c)]
    final = final[first + non_aegl_rest + aegl_cols]

    final["__key"] = final["Compound"].astype(str).str.strip().str.lower()
    final = final.drop_duplicates(subset="__key", keep="first").drop(columns="__key")

    final.to_csv(outputCsvPath, index=False)
    if verbose:
        print(f"Combined summary saved to: {outputCsvPath}")
    return final
