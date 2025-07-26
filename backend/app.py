from flask import Flask, jsonify, request
import pandas as pd
from Python_CWA_Tool import analyzeSingleAegl, nameToCompound, getCompoundAnalysis, compound_db
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # <-- this enables CORS for all routes

@app.route("/api/analyze", methods=["POST"])
def handleAnalyze():

    name = request.headers.get('name')

    if not name:
        return jsonify({"error": "No compound name provided"}), 400

    result = getCompoundAnalysis(name)
    return jsonify(result)

@app.route("/api/compoundNames", methods=["GET"])
def getCompoundNames():
    
    compoundNames = compound_db["Name"].tolist()
    return jsonify(compoundNames)

if __name__ == '__main__':
    app.run(debug=True)
