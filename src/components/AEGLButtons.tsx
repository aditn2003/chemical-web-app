import React, { useState } from "react";
import AEGLModal from "./AEGLModal";
import AeglGraph from "./AEGLGraph";
import GraphModal from "./GraphModal";

interface AEGLButtonsProps {
  aeglAnalysis: any[] | undefined;
}

const AEGLButtons = ({ aeglAnalysis }: AEGLButtonsProps) => {
  const [showValues, setShowValues] = useState(false);
  const [showTimes, setShowTimes] = useState(false);
  const [showGraphs, setShowGraphs] = useState(false);
  const [timeFilters, setTimeFilters] = useState<string[]>([
    "8hr",
    "4hr",
    "60min",
    "30min",
    "10min",
  ]);

  const timeOptions = ["8hr", "4hr", "60min", "30min", "10min"];
  const isEmpty = !aeglAnalysis || aeglAnalysis.length === 0;

  const toggleTime = (t: string) => {
    setTimeFilters((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
  };

  const renderValues = () => {
    if (isEmpty) return <p>No AEGL value data available.</p>;

    return (
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {aeglAnalysis.map((row, index) => (
          <div
            key={index}
            style={{
              flex: "1 1 28%",
              minWidth: "210px",
              fontSize: "0.8rem",
              padding: "0.75rem 1rem",
              border: "1px solid #ccc",
              borderRadius: "4px",
              boxSizing: "border-box",
            }}
          >
            <strong style={{ fontSize: "0.9rem" }}>
              AEGL {row.aeglLevel}-{row.timeStr} [mg/m³]:
            </strong>
            <div style={{ marginTop: "0.25rem" }}>
              {typeof row.aegl === "number" ? row.aegl.toFixed(4) : row.aegl}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderTimes = () => {
    if (isEmpty) return <p>No exposure time data available.</p>;

    return (
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {aeglAnalysis.map((row, index) => (
          <div
            key={index}
            style={{
              flex: "1 1 28%",
              minWidth: "210px",
              fontSize: "0.8rem",
              padding: "0.75rem 1rem",
              border: "1px solid #ccc",
              borderRadius: "4px",
              boxSizing: "border-box",
            }}
          >
            <strong>
              Time to reach AEGL-{row.aeglLevel} ({row.timeStr}):
            </strong>
            <div>
              {typeof row.tReach === "number"
                ? `${(row.tReach / 24).toFixed(2)} days`
                : "N/A"}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderGraphGrid = () => {
    if (isEmpty) return null;

    const filtered = aeglAnalysis.filter((row) =>
      timeFilters.includes(row.timeStr)
    );

    return (
      <>
        <div style={{ marginBottom: "1rem" }}>
          {timeOptions.map((t) => (
            <label key={t} style={{ marginRight: "1rem" }}>
              <input
                type="checkbox"
                checked={timeFilters.includes(t)}
                onChange={() => toggleTime(t)}
              />{" "}
              {t}
            </label>
          ))}
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "2rem",
            paddingBottom: "2rem",
          }}
        >
          {filtered.map((row, idx) => {
            if (!row.absorptionGraph || !row.fluxGraph) return null;

            return (
              <div
                key={idx}
                style={{
                  backgroundColor: "#fff",
                  border: "1px solid #ccc",
                  borderRadius: "10px",
                  padding: "1rem",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                  transition: "transform 0.3s",
                  cursor: "pointer",
                  height: "auto",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.transform =
                    "scale(1.03)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.transform = "scale(1)";
                }}
              >
                <h4 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>
                  AEGL-{row.aeglLevel} ({row.timeStr})
                </h4>
                <AeglGraph
                  absorptionGraph={row.absorptionGraph}
                  fluxGraph={row.fluxGraph}
                />
              </div>
            );
          })}
        </div>
      </>
    );
  };

  return (
    <>
      <button onClick={() => setShowValues(true)} style={{ margin: "1rem" }}>
        Show AEGL Values
      </button>
      <button onClick={() => setShowTimes(true)} style={{ margin: "1rem" }}>
        Show Exposure Times
      </button>
      <button onClick={() => setShowGraphs(true)} style={{ margin: "1rem" }}>
        Show AEGL Graphs
      </button>

      <AEGLModal
        title="AEGL Values"
        isOpen={showValues}
        onClose={() => setShowValues(false)}
      >
        {renderValues()}
      </AEGLModal>

      <AEGLModal
        title="Time to Reach Dermal Dose"
        isOpen={showTimes}
        onClose={() => setShowTimes(false)}
      >
        {renderTimes()}
      </AEGLModal>

      <GraphModal
        isOpen={showGraphs}
        onClose={() => setShowGraphs(false)}
        title="AEGL Graphs"
      >
        {renderGraphGrid()}
      </GraphModal>
    </>
  );
};

export default AEGLButtons;
