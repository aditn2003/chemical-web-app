import { useState } from "react";
import DropdownMenu from "./DropdownMenu";
import CombinedSummaryTable from "./CombinedSummaryTable";

export default function AnalysisView() {
  const [mode, setMode] = useState<"table" | "search">("table");

  return (
    <div>
      <button
        onClick={() => setMode(mode === "table" ? "search" : "table")}
        style={{ marginBottom: "1rem" }}
      >
        Switch to {mode === "table" ? "Search Mode" : "Table Mode"}
      </button>

      {mode === "table" ? <CombinedSummaryTable /> : <DropdownMenu />}
    </div>
  );
}
