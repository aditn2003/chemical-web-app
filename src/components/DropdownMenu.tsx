import React, { useEffect, useMemo, useRef, useState } from "react";
import CompoundInfo from "./CompoundInfo.tsx";
import ReactivityInfo from "./ReactivityInfo";
import AEGLButtons from "./AEGLButtons.tsx";
import KrPredictionCard from "./KrPrediction.tsx";

function DropdownMenu() {
  const [compoundNames, setCompoundNames] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlighted, setHighlighted] = useState<number>(-1);
  const listRef = useRef<HTMLUListElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

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
        body: JSON.stringify({ name }),
      });

      const data = await response.json();

      if (!response.ok || data?.error) {
        console.error(
          "Analyze error:",
          data?.error || `HTTP ${response.status}`
        );
        alert(data?.error || "Failed to analyze compound.");
        return;
      }

      if (!data.compound) {
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

  return (
    <div>
      <label
        htmlFor="chem-search"
        style={{ display: "block", marginBottom: 6 }}
      >
        Search chemical:
      </label>

      {/* Input + Analyze button side by side */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          flexWrap: "wrap",
          marginBottom: "1rem",
          maxWidth: "100%",
        }}
      >
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

      {/* Side-by-side cards */}
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

          {/* AEGL section below */}
          <div style={{ marginTop: "1.5rem" }}>
            {analysisResult.aeglAnalysis?.available ? (
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
