import React from "react";

interface KrPredictionProps {
  krPrediction: {
    compound: string;
    predicted_kr: number;
    confidence: string;
  };
}

const KrPredictionCard = ({ krPrediction }: KrPredictionProps) => {
  if (!krPrediction) return null;

  return (
    <div style={styles.card}>
      <h3>Predicted kₛ for: {krPrediction.compound}</h3>
      <p>
        <strong>Predicted kₛ Value:</strong> {krPrediction.predicted_kr}
      </p>
      <p>
        <strong>Confidence Level:</strong> {krPrediction.confidence}
      </p>
    </div>
  );
};

const styles = {
  card: {
    border: "1px solid #ccc",
    padding: "1rem",
    borderRadius: "8px",
    backgroundColor: "#f9f9f9",
    marginTop: "1.5rem",
    maxWidth: "500px",
  },
};

export default KrPredictionCard;
