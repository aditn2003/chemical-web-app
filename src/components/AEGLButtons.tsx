import React, { useState } from "react";
import AEGLModal from "./AEGLModal";

interface AEGLButtonsProps {
  aeglAnalysis: any[] | undefined;
}

const AEGLButtons = ({ aeglAnalysis }: AEGLButtonsProps) => {
  const [showValues, setShowValues] = useState(false);
  const [showTimes, setShowTimes] = useState(false);

  const isEmpty = !aeglAnalysis || aeglAnalysis.length === 0;

  const renderValues = () => {
    if (isEmpty) {
      return <p>No AEGL value data available for this compound.</p>;
    }

    return (
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "1rem",
          justifyContent: "flex-start",
        }}
      >
        {aeglAnalysis.map((row, index) => (
          <div
            key={index}
            style={{
              flex: "1 1 28%",
              border: "1px solid #ccc",
              borderRadius: "4px",
              padding: "0.75rem 1rem",
              minWidth: "210px",
              fontSize: "0.8rem",
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
    if (isEmpty) {
      return <p>No exposure time data available for this compound.</p>;
    }

    return (
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "1rem",
          justifyContent: "flex-start",
        }}
      >
        {aeglAnalysis.map((row, index) => (
          <div
            key={index}
            style={{
              flex: "1 1 28%",
              border: "1px solid #ccc",
              borderRadius: "4px",
              padding: "0.75rem 1rem",
              minWidth: "210px",
              fontSize: "0.8rem",
              boxSizing: "border-box",
            }}
          >
            <strong>
              Time to reach AEGL-{row.aeglLevel} ({row.timeStr}):
            </strong>
            <div>{(row.tReach / 24).toFixed(2)} days</div>
          </div>
        ))}
      </div>
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
    </>
  );
};

export default AEGLButtons;
