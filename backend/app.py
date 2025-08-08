from flask import Flask, jsonify, request
import pandas as pd
import os
from Python_CWA_Tool import analyze_reactivity, predict_kr, analyzeAllCompounds, compoundList, getCompoundAnalysis, compound_db, getGlobalScatterGraph, generateCombinedSummaryCsv
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # <-- this enables CORS for all routes

@app.route("/api/analyze", methods=["POST"])
def handleAnalyze():
    data = request.get_json()
    name = data.get('name') if data else None
    print("Received request with name:", name)

    if not name:
        return jsonify({"error": "No compound name provided"}), 400

    result = getCompoundAnalysis(name)
    return jsonify(result)


@app.route("/api/compoundNames", methods=["GET"])
def getCompoundNames():
    
    compoundNames = compound_db["Name"].tolist()
    return jsonify(compoundNames)

@app.route("/api/scattergraph", methods=["GET"])
def kr_scatter():
    graph_json = getGlobalScatterGraph()
    return jsonify({"graph": graph_json})


import traceback

@app.route("/api/combined-summary", methods=["GET"])
def get_combined_summary():
    try:
        df = generateCombinedSummaryCsv(verbose=True)
        return jsonify(df.to_dict(orient="records")), 200

    except Exception as e:
        print("ERROR in /api/combined-summary:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
