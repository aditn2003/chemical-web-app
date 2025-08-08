import React, { useEffect, useState } from "react";
import CompoundInfo from "./CoumpoundInfo.tsx";
import ReactivityInfo from "./ReactivityInfo";
import AEGLButtons from "./AEGLButtons.tsx";
import KrPredictionCard from "./KrPrediction.tsx";
import KrGraph from "./KrGraph.tsx";

function DropdownMenu() {
  const [selectedChemical, setSelectedChemical] = useState("");
  const [compoundNames, setCompoundNames] = useState<string[]>([]);
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Fetch compound names
  useEffect(() => {
    fetch("http://localhost:5000/api/compoundNames")
      .then((res) => res.json())
      .then((data) => setCompoundNames(data))
      .catch((err) => console.error("Error fetching compound names:", err));
  }, []);

  // Handle dropdown change
  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const newChemical = event.target.value;
    setSelectedChemical(newChemical);
    setAnalysisResult(null); // Clear old result
    console.log("Selected:", newChemical);
  };

  // Analyze button click
  const handleAnalyze = async () => {
    if (!selectedChemical) return;

    setIsAnalyzing(true);
    console.log("Sending analyze request for:", selectedChemical);

    try {
      const response = await fetch("http://localhost:5000/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: selectedChemical }),
      });

      const data = await response.json();
      console.log("Received response data:", data);

      setAnalysisResult(data);
      console.log("Analysis result:", data);
    } catch (err) {
      console.error("Error during analysis:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div>
      <label>Select chemical: </label>
      <select value={selectedChemical} onChange={handleChange}>
        <option value="">-- Choose a chemical --</option>
        {compoundNames.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>

      <button
        onClick={handleAnalyze}
        disabled={!selectedChemical || isAnalyzing}
        style={{ marginLeft: "1rem" }}
      >
        {isAnalyzing ? "Analyzing..." : "Analyze"}
      </button>
      <h2>
        Global k<sub>r</sub> Distribution
      </h2>
      <KrGraph />
      {analysisResult && (
        <>
          <CompoundInfo compound={analysisResult.compound} />
          <ReactivityInfo reactivity={analysisResult.reactivity} />
          <KrPredictionCard krPrediction={analysisResult.krPrediction} />
          <AEGLButtons aeglAnalysis={analysisResult.aeglAnalysis} />
        </>
      )}
    </div>
  );
}

export default DropdownMenu;
