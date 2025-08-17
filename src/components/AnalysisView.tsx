import { useState } from "react";
import DropdownMenu from "./DropdownMenu";
import CombinedSummaryTable from "./CombinedSummaryTable";
import TopBar from "./TopBar";

export default function AnalysisView() {
  const [mode, setMode] = useState<"table" | "search">("table");

  const toggleMode = () => {
    setMode((prev) => (prev === "table" ? "search" : "table"));
  };

  return (
    <div>
      <TopBar onToggleMode={toggleMode} mode={mode} />
      <div style={{ padding: "1.5rem" }}>
        {mode === "table" ? <CombinedSummaryTable /> : <DropdownMenu />}
      </div>
    </div>
  );
}
