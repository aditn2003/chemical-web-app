import React, { useMemo, useState } from "react";
import AEGLModal from "./AEGLModal";
import AeglGraph from "./AEGLGraph";
import GraphModal from "./GraphModal";
import Plot from "react-plotly.js";

type AeglRow = {
  aeglLevel: number | string;
  timeStr: string;
  aegl?: number | string | null;
  tReach?: number | null;
  // Present in gaseous mode; usually missing in aqueous mode:
  absorptionGraph?: string; // JSON string
  fluxGraph?: string; // JSON string
};

interface AEGLButtonsProps {
  aeglAnalysis?: AeglRow[];
  // Tell the component which mode we are in
  mode?: "gaseous" | "aqueous";
  // Optional: pass top-level 4 quick plots to use as a fallback for aqueous
  overviewGraphs?: Record<string, string> | null;
}

const timeOptions = ["8hr", "4hr", "60min", "30min", "10min"];

const AEGLButtons = ({
  aeglAnalysis,
  mode = "gaseous",
  overviewGraphs,
}: AEGLButtonsProps) => {
  const [showValues, setShowValues] = useState(false);
  const [showTimes, setShowTimes] = useState(false);
  const [showGraphs, setShowGraphs] = useState(false);

  const isEmpty = !aeglAnalysis || aeglAnalysis.length === 0;

  // Per-row graphs exist? (typical for gaseous)
  const hasRowGraphs = useMemo(
    () =>
      !!aeglAnalysis?.some(
        (r) =>
          typeof r?.absorptionGraph === "string" &&
          typeof r?.fluxGraph === "string"
      ),
    [aeglAnalysis]
  );

  // Aqueous fallback: use top-level 4 quick plots if present
  const hasOverviewGraphs =
    !!overviewGraphs &&
    (overviewGraphs.vaporAbsorption ||
      overviewGraphs.liquidAbsorption ||
      overviewGraphs.vaporFlux ||
      overviewGraphs.liquidFlux);

  // Only show the Graphs button if we have either per-row graphs (gaseous) OR overview graphs (aqueous fallback)
  const canShowGraphs =
    hasRowGraphs || (mode === "aqueous" && hasOverviewGraphs);

  const [timeFilters, setTimeFilters] = useState<string[]>([...timeOptions]);
  const toggleTime = (t: string) => {
    setTimeFilters((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
  };

  const renderValues = () => {
    if (isEmpty) return <p>No AEGL value data available.</p>;
    return (
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {aeglAnalysis!.map((row, index) => (
          <div
            key={`${row.aeglLevel}-${row.timeStr}-${index}`}
            style={{
              flex: "1 1 28%",
              minWidth: 210,
              fontSize: "0.8rem",
              padding: "0.75rem 1rem",
              border: "1px solid #ccc",
              borderRadius: 6,
              boxSizing: "border-box",
              background: "#fff",
            }}
          >
            <strong style={{ fontSize: "0.9rem" }}>
              AEGL {row.aeglLevel}-{row.timeStr} [mg/m³]:
            </strong>
            <div style={{ marginTop: 4 }}>
              {typeof row.aegl === "number"
                ? row.aegl.toFixed(4)
                : row.aegl ?? "N/A"}
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
        {aeglAnalysis!.map((row, index) => (
          <div
            key={`${row.aeglLevel}-${row.timeStr}-${index}`}
            style={{
              flex: "1 1 28%",
              minWidth: 210,
              fontSize: "0.8rem",
              padding: "0.75rem 1rem",
              border: "1px solid #ccc",
              borderRadius: 6,
              boxSizing: "border-box",
              background: "#fff",
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

  // GRAPH MODAL CONTENT
  const renderGraphContent = () => {
    // 1) Preferred: per-row graphs (gaseous)
    if (hasRowGraphs) {
      const filtered = aeglAnalysis!.filter((row) =>
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
                  style={{ marginRight: 6 }}
                />
                {t}
              </label>
            ))}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
              gap: "1rem",
            }}
          >
            {filtered.map((row, idx) => {
              if (!row.absorptionGraph || !row.fluxGraph) return null;
              return (
                <div
                  key={`${row.aeglLevel}-${row.timeStr}-${idx}`}
                  style={{
                    backgroundColor: "#fff",
                    border: "1px solid #ccc",
                    borderRadius: 10,
                    padding: "1rem",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
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
    }

    // 2) Aqueous fallback: show the 4 overview plots in the modal
    if (mode === "aqueous" && hasOverviewGraphs) {
      const keys = [
        "vaporAbsorption",
        "liquidAbsorption",
        "vaporFlux",
        "liquidFlux",
      ] as const;

      const safeParse = (s: string | undefined) => {
        try {
          return s ? JSON.parse(s) : null;
        } catch {
          return null;
        }
      };

      return (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
            gap: "1rem",
          }}
        >
          {keys.map((k) => {
            const parsed = safeParse(overviewGraphs?.[k]);
            if (!parsed) return null;
            return (
              <div
                key={k}
                style={{
                  backgroundColor: "#fff",
                  border: "1px solid #ccc",
                  borderRadius: 10,
                  padding: "1rem",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                }}
              >
                <h4 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>
                  {k}
                </h4>
                <Plot data={parsed.data} layout={parsed.layout} />
              </div>
            );
          })}
        </div>
      );
    }

    // 3) Nothing to show
    return (
      <div
        style={{
          padding: "0.75rem 1rem",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          background: "#fff",
          color: "#374151",
          fontSize: 14,
        }}
      >
        No AEGL graphs available.
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

      {canShowGraphs && (
        <button onClick={() => setShowGraphs(true)} style={{ margin: "1rem" }}>
          Show AEGL Graphs
        </button>
      )}

      <AEGLModal
        title="AEGL Values"
        isOpen={showValues}
        onClose={() => setShowValues(false)}
      >
        {renderValues()}
      </AEGLModal>

      <AEGLModal
        title="Exposure Times"
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
        {renderGraphContent()}
      </GraphModal>
    </>
  );
};

export default AEGLButtons;
