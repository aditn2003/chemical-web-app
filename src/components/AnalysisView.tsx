import { useState } from "react";
import DropdownMenu from "./DropdownMenu";
import CombinedSummaryTable from "./CombinedSummaryTable";
import TopBar from "./TopBar";
import KrGraph from "./KrGraph";

export default function AnalysisView() {
  const [mode, setMode] = useState<"table" | "search">("table");
  const [tableSubmode, setTableSubmode] = useState<"summary" | "graph">(
    "summary"
  );

  const toggleMode = () => {
    setMode((prev) => (prev === "table" ? "search" : "table"));
  };

  return (
    <div>
      <TopBar onToggleMode={toggleMode} mode={mode} />
      <div style={{ padding: "1.5rem" }}>
        {mode === "table" ? (
          <>
            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                marginBottom: "1rem",
              }}
            >
              <div
                style={{
                  display: "inline-flex",
                  borderRadius: 10,
                  border: "1px solid #2b6cb0",
                  overflow: "hidden",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                }}
              >
                <button
                  onClick={() => setTableSubmode("summary")}
                  style={{
                    padding: "8px 14px",
                    background: tableSubmode === "summary" ? "#2b6cb0" : "#fff",
                    color: tableSubmode === "summary" ? "#fff" : "#2b6cb0",
                    border: "none",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Table
                </button>
                <button
                  onClick={() => setTableSubmode("graph")}
                  style={{
                    padding: "8px 14px",
                    background: tableSubmode === "graph" ? "#2b6cb0" : "#fff",
                    color: tableSubmode === "graph" ? "#fff" : "#2b6cb0",
                    border: "none",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  kr Graph
                </button>
              </div>
            </div>
            {tableSubmode === "summary" ? (
              <CombinedSummaryTable />
            ) : (
              <KrGraph />
            )}
          </>
        ) : (
          <DropdownMenu />
        )}
      </div>
    </div>
  );
}
