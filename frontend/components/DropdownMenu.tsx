import React, { useEffect, useMemo, useRef, useState } from "react";
import CompoundInfo from "./CompoundInfo.tsx";
import ReactivityInfo from "./ReactivityInfo.tsx";
import AEGLButtons from "./AEGLButtons.tsx";
import KrPredictionCard from "./KrPrediction.tsx";
import Plot from "react-plotly.js";

type Mode = "gaseous" | "aqueous";

type AeglFigureSet = {
  vaporAbsorption?: string;
  liquidAbsorption?: string;
  vaporFlux?: string;
  liquidFlux?: string;
};

type AeglGridGrouped = {
  groups: Record<string, AeglFigureSet>;
  sortedKeys: string[];
};

function parsePlotlyJSON(raw: unknown): { data: any[]; layout: any } | null {
  if (raw == null) return null;
  try {
    const s = typeof raw === "string" ? raw : String(raw);
    const obj = JSON.parse(s);
    if (obj && Array.isArray(obj.data) && obj.layout) {
      return { data: obj.data, layout: obj.layout };
    }
  } catch (e) {
    console.error("Failed to parse Plotly JSON:", e, raw);
  }
  return null;
}

function groupAeglGrid(
  grid: Record<string, unknown> | undefined | null
): AeglGridGrouped {
  const groups: Record<string, AeglFigureSet> = {};
  const FIG_KEYS = [
    "vaporAbsorption",
    "liquidAbsorption",
    "vaporFlux",
    "liquidFlux",
  ] as const;

  if (grid && typeof grid === "object") {
    Object.entries(grid).forEach(([k, v]) => {
      const lastUnderscore = k.lastIndexOf("_");
      if (lastUnderscore <= 0) return;
      const prefix = k.slice(0, lastUnderscore);
      const figName = k.slice(lastUnderscore + 1);
      if (!FIG_KEYS.includes(figName as any)) return;

      if (!groups[prefix]) groups[prefix] = {};
      (groups[prefix] as any)[figName] = typeof v === "string" ? v : String(v);
    });
  }

  const orderDur: Record<string, number> = {
    "8hr": 0,
    "4hr": 1,
    "60min": 2,
    "30min": 3,
    "10min": 4,
  };
  const sortedKeys = Object.keys(groups).sort((a, b) => {
    const [, aTier, aDur] = a.match(/^AEGL(\d)_(.+)$/) || [, "9", "zz"];
    const [, bTier, bDur] = b.match(/^AEGL(\d)_(.+)$/) || [, "9", "zz"];
    const tcmp = Number(aTier) - Number(bTier);
    if (tcmp !== 0) return tcmp;
    return (orderDur[aDur] ?? 99) - (orderDur[bDur] ?? 99);
  });

  return { groups, sortedKeys };
}

function DropdownMenu() {
  const [compoundNames, setCompoundNames] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlighted, setHighlighted] = useState<number>(-1);
  const listRef = useRef<HTMLUListElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [mode, setMode] = useState<Mode>("gaseous");

  useEffect(() => {
    fetch("http://localhost:5000/api/compoundNames")
      .then((res) => res.json())
      .then((data) => setCompoundNames(Array.isArray(data) ? data : []))
      .catch((err) => console.error("Error fetching compound names:", err));
  }, []);

  const suggestions = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return compoundNames.filter((n) => n.toLowerCase().includes(q)).slice(0, 8);
  }, [query, compoundNames]);

  const choose = (name: string) => {
    setQuery(name);
    setShowSuggestions(false);
    setHighlighted(-1);
    setAnalysisResult(null);
    handleAnalyze(name);
  };

  const handleAnalyze = async (overrideName?: string) => {
    const name = (overrideName || query).trim();
    if (!name) return;

    setIsAnalyzing(true);
    setAnalysisResult(null);

    try {
      const response = await fetch("http://localhost:5000/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, mode }),
      });

      const data = await response.json();

      if (
        !response.ok ||
        (data && typeof data === "object" && "error" in data)
      ) {
        console.error(
          "Analyze error:",
          (data as any)?.error || `HTTP ${response.status}`
        );
        alert((data as any)?.error || "Failed to analyze compound.");
        return;
      }

      if (!data || !data.compound) {
        alert("No compound details returned from server.");
        return;
      }

      setAnalysisResult(data);
    } catch (err) {
      console.error("Error during analysis:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showSuggestions && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      setShowSuggestions(true);
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((h) => Math.min(h + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter") {
      if (
        showSuggestions &&
        highlighted >= 0 &&
        highlighted < suggestions.length
      ) {
        choose(suggestions[highlighted]);
      } else {
        handleAnalyze();
      }
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
      setHighlighted(-1);
    }
  };

  useEffect(() => {
    const onDocClick = (ev: MouseEvent) => {
      const target = ev.target as Node;
      if (
        inputRef.current &&
        !inputRef.current.contains(target) &&
        listRef.current &&
        !listRef.current.contains(target)
      ) {
        setShowSuggestions(false);
        setHighlighted(-1);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const grouped: AeglGridGrouped | null = useMemo(() => {
    if (mode !== "aqueous" || !analysisResult?.aeglGraphGrid) return null;
    return groupAeglGrid(
      analysisResult.aeglGraphGrid as Record<string, unknown>
    );
  }, [mode, analysisResult?.aeglGraphGrid]);

  const [activeAegl, setActiveAegl] = useState<string | null>(null);

  useEffect(() => {
    if (grouped && grouped.sortedKeys.length > 0) {
      setActiveAegl((prev) =>
        prev && grouped.groups[prev] ? prev : grouped.sortedKeys[0]
      );
    } else {
      setActiveAegl(null);
    }
  }, [grouped]);

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "1rem",
          flexWrap: "wrap",
          marginBottom: "1.25rem",
        }}
      >
        {/* Mode dropdown */}
        <label style={{ fontSize: 14, whiteSpace: "nowrap" }}>
          Select Mode:
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as Mode)}
            style={{
              marginLeft: 8,
              padding: "6px 12px",
              borderRadius: 6,
              border: "1px solid #ccc",
              fontSize: 14,
            }}
          >
            <option value="gaseous">Gaseous</option>
            <option value="aqueous">Aqueous</option>
          </select>
        </label>

        {/* Search label */}
        <label
          htmlFor="chem-search"
          style={{ fontSize: 14, whiteSpace: "nowrap" }}
        >
          Search chemical:
        </label>

        {/* Search input */}
        <div
          role="combobox"
          aria-expanded={showSuggestions}
          aria-owns="chem-suggestions"
          aria-haspopup="listbox"
          aria-controls="chem-suggestions"
          aria-label="Chemical search"
          style={{ position: "relative", width: 360, maxWidth: "100%" }}
        >
          <input
            id="chem-search"
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setShowSuggestions(true);
              setAnalysisResult(null);
            }}
            onKeyDown={onKeyDown}
            placeholder="Type a name or CAS (free text supported)"
            autoComplete="off"
            style={{
              width: "100%",
              padding: "8px 12px",
              fontSize: 14,
              border: "1px solid #d1d5db",
              borderRadius: 9999,
              outline: "none",
              background: "#f9fafb",
              transition: "box-shadow 0.2s ease",
              boxShadow: "inset 0 1px 2px rgba(0,0,0,0.05)",
            }}
            onFocusCapture={(e) =>
              (e.currentTarget.style.boxShadow =
                "0 0 0 3px rgba(59,130,246,0.35)")
            }
            onBlurCapture={(e) =>
              (e.currentTarget.style.boxShadow =
                "inset 0 1px 2px rgba(0,0,0,0.05)")
            }
          />

          {showSuggestions && suggestions.length > 0 && (
            <ul
              id="chem-suggestions"
              ref={listRef}
              role="listbox"
              style={{
                position: "absolute",
                zIndex: 20,
                top: "110%",
                left: 0,
                right: 0,
                margin: 0,
                padding: 6,
                listStyle: "none",
                background: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: 10,
                boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
                maxHeight: 260,
                overflowY: "auto",
              }}
            >
              {suggestions.map((name, i) => (
                <li
                  key={name}
                  role="option"
                  aria-selected={i === highlighted}
                  onMouseEnter={() => setHighlighted(i)}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    choose(name);
                  }}
                  style={{
                    padding: "8px 10px",
                    borderRadius: 8,
                    cursor: "pointer",
                    background: i === highlighted ? "#f3f4f6" : "transparent",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                  title={name}
                >
                  {name}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Analyze button */}
        <button
          onClick={() => handleAnalyze()}
          disabled={isAnalyzing || !query.trim()}
          style={{
            padding: "8px 14px",
            borderRadius: 10,
            border: "1px solid #2b6cb0",
            background: "#2b6cb0",
            color: "#fff",
            fontWeight: 600,
            cursor: isAnalyzing ? "default" : "pointer",
            height: 40,
          }}
        >
          {isAnalyzing ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {/* Analysis results */}
      {analysisResult?.compound && (
        <>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "1.5rem",
              marginTop: "1rem",
            }}
          >
            <CompoundInfo compound={analysisResult.compound} />
            {analysisResult.reactivity && (
              <ReactivityInfo reactivity={analysisResult.reactivity} />
            )}
            {analysisResult.krPrediction && (
              <KrPredictionCard krPrediction={analysisResult.krPrediction} />
            )}
          </div>

          {/* AEGL Visualization */}
          <div style={{ marginTop: "1.5rem" }}>
            {mode === "aqueous" ? (
              <>
                {grouped && grouped.sortedKeys.length > 0 ? (
                  <div style={{ display: "grid", gap: "0.75rem" }}>
                    {/* Chip row */}
                    <div
                      style={{
                        display: "flex",
                        flexWrap: "wrap",
                        gap: "8px",
                        alignItems: "center",
                      }}
                    >
                      {grouped.sortedKeys.map((k: string) => {
                        const isActive = activeAegl === k;
                        return (
                          <button
                            key={k}
                            onClick={() => setActiveAegl(k)}
                            style={{
                              padding: "6px 9px",
                              borderRadius: 9999,
                              border: "1px solid #e5e7eb",
                              background: isActive ? "#111827" : "#ffffff",
                              color: isActive ? "#ffffff" : "#111827",
                              fontSize: 14,
                              fontWeight: 700,
                              cursor: "pointer",
                              lineHeight: 1.3,
                              boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
                            }}
                          >
                            {k}
                          </button>
                        );
                      })}
                    </div>

                    {/* Active target panel */}
                    {activeAegl
                      ? (() => {
                          const g = grouped.groups[activeAegl!];
                          const vA = parsePlotlyJSON(g?.vaporAbsorption);
                          const lA = parsePlotlyJSON(g?.liquidAbsorption);
                          const vF = parsePlotlyJSON(g?.vaporFlux);
                          const lF = parsePlotlyJSON(g?.liquidFlux);

                          if (!vA && !lA && !vF && !lF) {
                            return (
                              <div
                                style={{
                                  padding: "10px 16px",
                                  borderRadius: 9999,
                                  border: "1px solid #e5e7eb",
                                  background: "#111827",
                                  color: "#ffffff",
                                  fontSize: 14,
                                  fontWeight: 700,
                                  lineHeight: 1.2,
                                  boxShadow: "0 2px 4px rgba(0,0,0,0.06)",
                                }}
                              >
                                No plots available for{" "}
                                <strong>{activeAegl}</strong>.
                              </div>
                            );
                          }
                          const withLegendBelow = (lay: any) => ({
                            ...lay,
                            autosize: true,
                            margin: { t: 30, r: 20, b: 72, l: 48 },
                            legend: {
                              orientation: "h",
                              x: 0.5,
                              xanchor: "center",
                              y: -0.15,
                              yanchor: "top",
                              font: { size: 12 },
                              bgcolor: "rgba(255,255,255,0.75)",
                            },
                            title: {
                              ...(typeof lay?.title === "object"
                                ? lay.title
                                : { text: lay?.title }),
                              font: { size: 13 },
                            },
                          });

                          const Cell: React.FC<{ fig: any | null }> = ({
                            fig,
                          }) =>
                            fig ? (
                              <div
                                style={{
                                  width: "100%",
                                  height: 380,
                                  minWidth: 0,
                                }}
                              >
                                <Plot
                                  data={fig.data}
                                  layout={withLegendBelow(fig.layout)}
                                  useResizeHandler
                                  style={{ width: "100%", height: "100%" }}
                                  config={{
                                    displayModeBar: false,
                                    responsive: true,
                                  }}
                                />
                              </div>
                            ) : null;

                          return (
                            <div
                              style={{
                                display: "grid",
                                gridTemplateColumns:
                                  "repeat(2, minmax(0, 1fr))",
                                gridAutoRows: "380px",
                                gap: "0.75rem",
                                paddingTop: "0.5rem",
                                alignItems: "stretch",
                                justifyItems: "stretch",
                              }}
                            >
                              <Cell fig={vA} />
                              <Cell fig={lA} />
                              <Cell fig={vF} />
                              <Cell fig={lF} />
                            </div>
                          );
                        })()
                      : null}
                  </div>
                ) : (
                  <div
                    style={{
                      padding: "0.75rem 1rem",
                      border: "1px solid #e5e7eb",
                      borderRadius: 8,
                      background: "#fff",
                      boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
                      color: "#374151",
                      fontSize: 14,
                    }}
                  >
                    <strong>No aqueous AEGL plots to display.</strong>{" "}
                    {analysisResult?.aeglAnalysis?.reason ||
                      "No valid AEGL targets found for this compound."}
                  </div>
                )}
              </>
            ) : analysisResult.aeglAnalysis?.available ? (
              <AEGLButtons aeglAnalysis={analysisResult.aeglAnalysis.results} />
            ) : (
              <div
                style={{
                  padding: "0.75rem 1rem",
                  border: "1px solid #e5e7eb",
                  borderRadius: 8,
                  background: "#fff",
                  boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
                  color: "#374151",
                  fontSize: 14,
                }}
              >
                <strong>AEGL data unavailable.</strong>{" "}
                {analysisResult.aeglAnalysis?.reason ||
                  "No AEGL thresholds found for this compound."}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default DropdownMenu;
