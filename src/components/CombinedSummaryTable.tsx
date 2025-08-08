import { useEffect, useMemo, useState } from "react";

type DetailMode = "aegl" | "times";

function Modal({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
        zIndex: 1000,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        style={{
          background: "#fff",
          borderRadius: 12,
          maxWidth: 900,
          width: "100%",
          boxShadow: "0 10px 30px rgba(0,0,0,0.2)",
          padding: 18,
        }}
      >
        <div
          style={{ display: "flex", justifyContent: "space-between", gap: 8 }}
        >
          <h3 style={{ margin: 0 }}>{title}</h3>
          <button onClick={onClose} style={{ fontWeight: 600 }}>
            ✕
          </button>
        </div>
        <div style={{ marginTop: 12 }}>{children}</div>
      </div>
    </div>
  );
}

export default function CombinedSummaryTable() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState("");
  const [modalCols, setModalCols] = useState<string[]>([]);
  const [modalRow, setModalRow] = useState<any | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("http://localhost:5000/api/combined-summary");
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        const data = await res.json();
        setRows(Array.isArray(data) ? data : []);
      } catch (e: any) {
        console.error(e);
        setError(e?.message || "Error loading summary");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const priority = ["Compound", "CAS", "Class", "MW", "LogP", "Predicted_kr"];

  const isAeglValueCol = (k: string) =>
    /AEGL.*\(mg\/m³\)|- AEGL \(mg\/m³\)/i.test(k);
  const isLagCol = (k: string) => /Lag Time \(hr\)/i.test(k);
  const isTimeDoseHrCol = (k: string) => /Time to Dose \(hr\)/i.test(k);
  const isTimeDoseDaysCol = (k: string) => /Time to Dose \(days\)/i.test(k);

  const baseColumns = useMemo(() => {
    const sample = rows[0] ?? {};
    const all = Object.keys(sample);
    const first: string[] = [];
    for (const key of priority) if (all.includes(key)) first.push(key);
    const rest = all.filter((k) => !first.includes(k));
    return [...first, ...rest].filter(
      (c) =>
        !isAeglValueCol(c) &&
        !isLagCol(c) &&
        !isTimeDoseHrCol(c) &&
        !isTimeDoseDaysCol(c)
    );
  }, [rows]);

  const allCols = useMemo(() => Object.keys(rows[0] ?? {}), [rows]);

  const fmt = (col: string, val: any) => {
    const isEmpty =
      val === null ||
      val === undefined ||
      (typeof val === "number" && Number.isNaN(val)) ||
      (typeof val === "string" &&
        (val.trim() === "" ||
          val.trim() === "-" ||
          val.trim().toLowerCase() === "nan"));

    if (isEmpty) return "undefined";

    if (col === "Predicted_kr" && typeof val === "number")
      return val.toExponential(3);
    if ((col === "MW" || col === "LogP") && typeof val === "number")
      return val.toFixed(2);

    return String(val);
  };

  const pill = (primary = false) =>
    ({
      padding: "6px 10px",
      borderRadius: 8,
      border: "1px solid #2b6cb0",
      background: primary ? "#2b6cb0" : "#e6f0ff",
      color: primary ? "#fff" : "#1a365d",
      cursor: "pointer",
      fontSize: 14,
      fontWeight: 600,
    } as const);

  const openModal = (row: any, mode: DetailMode) => {
    const cols =
      mode === "aegl"
        ? allCols.filter(isAeglValueCol)
        : allCols.filter(isTimeDoseHrCol);

    setModalRow(row);
    setModalCols(cols);
    setModalTitle(
      `${mode === "aegl" ? "AEGL Values" : "AEGL Exposure Times (hr)"} — ${
        row.Compound ?? ""
      }`
    );
    setModalOpen(true);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) =>
      e.key === "Escape" && setModalOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const filteredRows = useMemo(() => {
    if (!query.trim()) return rows;
    const q = query.trim().toLowerCase();
    return rows.filter(
      (r) =>
        String(r.Compound ?? "")
          .toLowerCase()
          .includes(q) ||
        String(r.CAS ?? "")
          .toLowerCase()
          .includes(q)
    );
  }, [rows, query]);

  return (
    <>
      {loading && <div>Loading...</div>}
      {!loading && error && <div className="text-red-600">{error}</div>}
      {!loading && !error && rows.length === 0 && <div>No data found</div>}

      {!loading && !error && rows.length > 0 && (
        <>
          {/* Search bar */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              margin: "0 0 8px 0",
            }}
          >
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder=" Search compound or CAS..."
              style={{
                width: 320,
                padding: "8px 12px",
                fontSize: 13,
                border: "1px solid #d1d5db",
                borderRadius: "9999px",
                outline: "none",
                background: "#f9fafb",
                transition: "all 0.2s ease",
                boxShadow: "inset 0 1px 2px rgba(0,0,0,0.05)",
              }}
              onFocus={(e) =>
                (e.target.style.boxShadow = "0 0 0 3px rgba(59,130,246,0.4)")
              }
              onBlur={(e) =>
                (e.target.style.boxShadow = "inset 0 1px 2px rgba(0,0,0,0.05)")
              }
            />

            {query && (
              <button
                onClick={() => setQuery("")}
                style={{
                  fontSize: 12,
                  padding: "6px 10px",
                  borderRadius: "9999px",
                  border: "1px solid #d1d5db",
                  background: "#fff",
                  cursor: "pointer",
                  transition: "background 0.2s ease",
                }}
                onMouseOver={(e) =>
                  (e.currentTarget.style.background = "#f3f4f6")
                }
                onMouseOut={(e) => (e.currentTarget.style.background = "#fff")}
              >
                Clear
              </button>
            )}
            <div style={{ marginLeft: "auto", fontSize: 12, color: "#6b7280" }}>
              {filteredRows.length} result{filteredRows.length === 1 ? "" : "s"}
            </div>
          </div>
          {/* Table */}
          <div
            style={{
              overflowX: "auto",
              margin: 0,
              padding: "0.5rem",
            }}
          >
            <table
              style={{
                borderCollapse: "collapse",
                width: "100%",
                background: "#fff",
                borderRadius: "8px",
                boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
                fontSize: "13px",
                lineHeight: "1.3",
              }}
            >
              <thead>
                <tr>
                  {baseColumns.map((col) => (
                    <th
                      key={col}
                      style={{
                        background: "#f8f9fa",
                        padding: "6px 8px",
                        textAlign: "left",
                        borderBottom: "1px solid #e5e7eb",
                        fontWeight: 600,
                      }}
                    >
                      {col}
                    </th>
                  ))}
                  <th
                    style={{
                      background: "#f8f9fa",
                      padding: "6px 8px",
                      textAlign: "left",
                      borderBottom: "1px solid #e5e7eb",
                      fontWeight: 600,
                    }}
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row, idx) => {
                  const key = row.Compound ?? String(idx);
                  return (
                    <tr
                      key={key}
                      style={{
                        background: idx % 2 === 0 ? "#ffffff" : "#fafafa",
                      }}
                    >
                      {baseColumns.map((col) => (
                        <td
                          key={col}
                          style={{
                            padding: "6px 8px",
                            borderBottom: "1px solid #e5e7eb",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {fmt(col, row[col])}
                        </td>
                      ))}
                      <td
                        style={{
                          padding: "6px 8px",
                          borderBottom: "1px solid #e5e7eb",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            gap: 6,
                            justifyContent: "flex-end",
                          }}
                        >
                          <button
                            style={{
                              ...pill(true),
                              fontSize: "12px",
                              padding: "4px 8px",
                            }}
                            onClick={() => openModal(row, "aegl")}
                          >
                            AEGL Values
                          </button>
                          <button
                            style={{
                              ...pill(false),
                              fontSize: "12px",
                              padding: "4px 8px",
                            }}
                            onClick={() => openModal(row, "times")}
                          >
                            AEGL Exposure Time
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <Modal
            open={modalOpen}
            title={modalTitle}
            onClose={() => setModalOpen(false)}
          >
            {modalRow && (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, minmax(0,1fr))",
                  gap: 10,
                }}
              >
                {modalCols.map((c) => (
                  <div key={c} style={{ fontSize: 14 }}>
                    <div style={{ fontWeight: 700 }}>{c}</div>
                    <div>{fmt(c, modalRow[c])}</div>
                  </div>
                ))}
              </div>
            )}
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                marginTop: 16,
              }}
            >
              <button
                style={{ ...pill(true), padding: "8px 14px" }}
                onClick={() => setModalOpen(false)}
              >
                Close
              </button>
            </div>
          </Modal>
        </>
      )}
    </>
  );
}
