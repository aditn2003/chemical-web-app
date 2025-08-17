from data_loader import compound_db, compoundList, nameToCompound
from pubchem_utils import build_compound, hasAeglSupport
from analysis_core import analyze_reactivity, predict_kr, analyzeAllAegls, makeJsonSafe, generateCombinedSummaryCsv

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

if __name__ == "__main__":
    from analysis_core import analyzeAllCompounds
    analyzeAllCompounds(compoundList, verbose=False)
    generateCombinedSummaryCsv(verbose=True)
