import { useEffect, useState } from "react";
import Plot from "react-plotly.js";

function KrGraph() {
  const [graphData, setGraphData] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("http://localhost:5000/api/scattergraph")
      .then((res) => res.json())
      .then((data) => {
        try {
          const parsed = JSON.parse(data.graph);
          setGraphData(parsed);
        } catch (err) {
          setError("Failed to parse graph JSON");
        }
      })
      .catch((err) => {
        setError("Error fetching scatter graph");
        console.error(err);
      });
  }, []);

  if (error) return <div className="text-red-600">{error}</div>;
  if (!graphData) return <div>Loading scatter plot...</div>;

  return (
    <Plot
      data={graphData.data}
      layout={{
        ...graphData.layout,
        autosize: true,
        margin: { l: 50, r: 30, t: 50, b: 50 },
      }}
      config={{ responsive: true }}
      style={{ width: "100%", height: "100%", minHeight: 500 }}
    />
  );
}

export default KrGraph;
