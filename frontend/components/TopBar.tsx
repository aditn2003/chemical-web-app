import React from "react";
import "../App.css";

interface TopBarProps {
  onToggleMode: () => void;
  mode: "table" | "search";
}

const TopBar = ({ onToggleMode, mode }: TopBarProps) => {
  return (
    <header style={styles.header}>
      <h1 style={styles.title}>AEGL Analysis Dashboard</h1>
      <button className="mode-switch-button" onClick={onToggleMode}>
        Switch to {mode === "table" ? "Search Mode" : "Table Mode"}
      </button>
    </header>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "1rem 2rem",
    backgroundColor: "#f8f9fb",
    borderBottom: "1px solid #ccc",
    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.05)",
    position: "sticky",
    top: 0,
    zIndex: 1000,
  },
  title: {
    fontSize: "1.5rem",
    fontWeight: "bold",
    margin: 0,
    color: "#333",
  },
};

export default TopBar;
