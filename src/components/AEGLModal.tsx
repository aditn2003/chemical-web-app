import React from "react";

interface AEGLModalProps {
  title: string;
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

const AEGLModal = ({ title, isOpen, onClose, children }: AEGLModalProps) => {
  if (!isOpen) return null;

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <h2>{title}</h2>
        <div style={styles.content}>{children}</div>
        <button onClick={onClose} style={styles.closeButton}>
          Close
        </button>
      </div>
    </div>
  );
};

const styles = {
  overlay: {
    position: "fixed" as const,
    top: 0,
    left: 0,
    width: "100vw",
    height: "100vh",
    backgroundColor: "rgba(0,0,0,0.5)",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 1000,
  },
  modal: {
    backgroundColor: "#fff",
    padding: "2rem",
    borderRadius: "8px",
    maxWidth: "900px",
    width: "90%",
    maxHeight: "90vh",
    overflowY: "auto",
  } as React.CSSProperties,
  content: {
    display: "flex",
    flexWrap: "wrap" as const,
    gap: "1rem",
    justifyContent: "flex-start",
  },
  closeButton: {
    backgroundColor: "red",
    color: "white",
    padding: "0.5rem 1rem",
    marginTop: "1rem",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
  },
};

export default AEGLModal;
