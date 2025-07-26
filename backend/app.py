from flask import Flask, jsonify, request
import pandas as pd
from Python_CWA_Tool import analyzeSingleAegl, nameToCompound, getCompoundAnalysis

app = Flask(__name__)

@app.route("/api/analyze", methods=["POST"])
def analyze():

    ## Send data using body 
    # data = request.get_json()
    # name = data.get('name')

    ## Send data using header 
    name = request.headers.get('name')

    if not name:
        return jsonify({"error": "No compound name provided"}), 400

    result = getCompoundAnalysis(name)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
