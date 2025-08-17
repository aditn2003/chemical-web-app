import React from "react";

const GraphModal = ({
  isOpen,
  title,
  onClose,
  children,
}: {
  isOpen: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) => {
  if (!isOpen) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        style={{
          width: "100%",
          height: "90%",
          maxWidth: "96rem",
          background: "#fff",
          borderRadius: 12,
          overflowY: "auto",
          padding: "24px 32px",
          boxShadow: "0 10px 40px rgba(0,0,0,0.25)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 16,
          }}
        >
          <h2 style={{ margin: 0 }}>{title}</h2>
          <button onClick={onClose} style={{ fontSize: 16, fontWeight: 600 }}>
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
};

export default GraphModal;
