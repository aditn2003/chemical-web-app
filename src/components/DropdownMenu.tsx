import React, { useEffect, useMemo, useRef, useState } from "react";
import CompoundInfo from "./CompoundInfo.tsx";
import ReactivityInfo from "./ReactivityInfo";
import AEGLButtons from "./AEGLButtons.tsx";
import KrPredictionCard from "./KrPrediction.tsx";
import KrGraph from "./KrGraph.tsx";

function DropdownMenu() {
  // raw list from backend
  const [compoundNames, setCompoundNames] = useState<string[]>([]);
  // current query text in the search bar
  const [query, setQuery] = useState("");
  // selected chemical for analyze
  const [selectedChemical, setSelectedChemical] = useState("");
  // analysis response
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlighted, setHighlighted] = useState<number>(-1);
  const listRef = useRef<HTMLUListElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Fetch compound names for suggestions
  useEffect(() => {
    fetch("http://localhost:5000/api/compoundNames")
      .then((res) => res.json())
      .then((data) => setCompoundNames(Array.isArray(data) ? data : []))
      .catch((err) => console.error("Error fetching compound names:", err));
  }, []);

  // top 8 suggestions that are case-insensitive
  const suggestions = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return compoundNames.filter((n) => n.toLowerCase().includes(q)).slice(0, 8);
  }, [query, compoundNames]);

  // commit selection from suggestions
  const choose = (name: string) => {
    setQuery(name);
    setSelectedChemical(name);
    setShowSuggestions(false);
    setHighlighted(-1);
    setAnalysisResult(null);
  };

  const handleAnalyze = async () => {
    const name = (selectedChemical || query).trim();
    if (!name) return;

    setIsAnalyzing(true);
    setAnalysisResult(null);
    try {
      const response = await fetch("http://localhost:5000/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const data = await response.json();

      if (!response.ok || (data && data.error)) {
        setAnalysisResult(null);
        console.error(
          "Analyze error:",
          data?.error || `HTTP ${response.status}`
        );
        alert(data?.error || "Failed to analyze compound.");
        return;
      }

      if (!data.compound) {
        setAnalysisResult(null);
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
        setSelectedChemical(query.trim());
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

  return (
    <div>
      <label
        htmlFor="chem-search"
        style={{ display: "block", marginBottom: 6 }}
      >
        Search chemical:
      </label>

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
            setSelectedChemical("");
            setShowSuggestions(true);
            setAnalysisResult(null);
          }}
          onKeyDown={onKeyDown}
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
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

      <button
        onClick={handleAnalyze}
        disabled={isAnalyzing || (!query.trim() && !selectedChemical)}
        style={{
          marginLeft: 12,
          padding: "8px 14px",
          borderRadius: 10,
          border: "1px solid #2b6cb0",
          background: "#2b6cb0",
          color: "#fff",
          fontWeight: 600,
          cursor: isAnalyzing ? "default" : "pointer",
        }}
      >
        {isAnalyzing ? "Analyzing..." : "Analyze"}
      </button>

      <h2 style={{ marginTop: "1rem" }}>
        Global k<sub>r</sub> Distribution
      </h2>
      <KrGraph />

      {analysisResult?.compound && (
        <>
          <CompoundInfo compound={analysisResult.compound} />
          {analysisResult.reactivity && (
            <ReactivityInfo reactivity={analysisResult.reactivity} />
          )}
          {analysisResult.krPrediction && (
            <KrPredictionCard krPrediction={analysisResult.krPrediction} />
          )}

          {analysisResult.aeglAnalysis?.available ? (
            <AEGLButtons aeglAnalysis={analysisResult.aeglAnalysis.results} />
          ) : (
            <div
              style={{
                marginTop: "1rem",
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
        </>
      )}
    </div>
  );
}

export default DropdownMenu;
