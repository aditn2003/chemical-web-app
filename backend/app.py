from flask import Flask, jsonify, request
import pandas as pd
import os
from analysis_core import getGlobalScatterGraph, analyzeAllCompounds
from pubchem_utils import build_compound, hasAeglSupport
from data_loader import compound_db, compoundList
from analysis_core import analyze_reactivity, predict_kr, analyzeAllAegls, makeJsonSafe, generateCombinedSummaryCsv, analyzeSingleAegl
from flask_cors import CORS
import traceback
from aqueous_code import run_all_aegl
import plotly.io as pio


app = Flask(__name__)
CORS(app)  # <-- this enables CORS for all routes

if not os.path.exists("aegl_results.csv") or not os.path.exists("kr_predictions_135.csv"):
    print("[Boot] Missing summary files — running analysis...")
    analyzeAllCompounds(compoundList, verbose=False)
    generateCombinedSummaryCsv(verbose=True)
else:
    print("[Boot] Summary files already exist.")

def getCompoundAnalysis(name):
    compound = build_compound(name, compound_db, makeJsonSafe)
    if not compound:
        return {"error": f"Compound '{name}' not found."}

    reactivity = analyze_reactivity(compound)
    krPrediction = predict_kr(compound)
    aegl_available, reason = hasAeglSupport(compound)

    if aegl_available:
        times = ["8hr", "4hr", "60min", "30min", "10min"]
        results = analyzeAllAegls(compound, times)
        aeglAnalysis = {"available": True, "results": results}
    else:
        aeglAnalysis = {"available": False, "reason": reason}

    return makeJsonSafe({
        "compound": compound,
        "reactivity": reactivity,
        "krPrediction": krPrediction,
        "aeglAnalysis": aeglAnalysis
    })

@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()
        if not data or "name" not in data:
            return jsonify({"error": "Missing compound name"}), 400

        name = str(data["name"]).strip()
        mode = str(data.get("mode", "gaseous")).lower()

        if mode == "gaseous":
            result = getCompoundAnalysis(name)
            return jsonify(result)

        elif mode == "aqueous":
            try:
                all_figs = run_all_aegl(name=name)

                result = getCompoundAnalysis(name)

                result["aeglGraphGrid"] = all_figs

                duration_order = ["8hr", "4hr", "60min", "30min", "10min"]
                overview = {"vaporAbsorption": None,
                            "liquidAbsorption": None,
                            "vaporFlux": None,
                            "liquidFlux": None}

                chosen_key_prefix = None
                for tier in (1, 2, 3):
                    for dur in duration_order:
                        prefix = f"AEGL{tier}_{dur}_"
                        has_all_four = all(
                            f"{prefix}{k}" in all_figs
                            for k in overview.keys()
                        )
                        if has_all_four:
                            chosen_key_prefix = prefix
                            break
                    if chosen_key_prefix:
                        break

                if chosen_key_prefix:
                    overview = {
                        "vaporAbsorption": all_figs[f"{chosen_key_prefix}vaporAbsorption"],
                        "liquidAbsorption": all_figs[f"{chosen_key_prefix}liquidAbsorption"],
                        "vaporFlux":       all_figs[f"{chosen_key_prefix}vaporFlux"],
                        "liquidFlux":      all_figs[f"{chosen_key_prefix}liquidFlux"],
                    }
                result["aeglGraphs"] = overview

                if isinstance(result.get("aeglAnalysis"), dict):
                    result["aeglAnalysis"]["source"] = "aqueous_model"
                    result["aeglAnalysis"]["available"] = True
                else:
                    result["aeglAnalysis"] = {"available": True, "source": "aqueous_model"}

                return jsonify(result)

            except Exception as e:
                return jsonify({"error": f"Aqueous model error: {str(e)}"}), 500

        else:
            return jsonify({"error": f"Unsupported mode '{mode}'"}), 400

    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@app.route("/api/compoundNames", methods=["GET"])
def getCompoundNames():
    
    compoundNames = compound_db["Name"].tolist()
    return jsonify(compoundNames)

@app.route("/api/scattergraph", methods=["GET"])
def kr_scatter():
    graph_json = getGlobalScatterGraph()
    return jsonify({"graph": graph_json})

@app.route("/api/combined-summary", methods=["GET"])
def get_combined_summary():
    try:
        df = generateCombinedSummaryCsv(verbose=True)
        return jsonify(df.to_dict(orient="records")), 200

    except Exception as e:
        print("ERROR in /api/combined-summary:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/aegl-graph", methods=["GET"])
def aegl_graph():
    name = request.args.get("name")           
    level = int(request.args.get("level", 1))
    timeStr = request.args.get("time", "8hr")

    comp = build_compound(name)
    if not comp:
        return jsonify({"error": f"Compound '{name}' not found"}), 404

    result = analyzeSingleAegl(comp, level, timeStr, includeGraphs=True)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
