import React from "react";

interface CompoundInfoProps {
  compound: {
    Name: string;
    formula?: string;
    MW?: number;
    CAS?: string;
    class?: string;
    SMILES?: string;
  };
}

const CompoundInfo: React.FC<CompoundInfoProps> = ({ compound }) => {
  return (
    <div
      style={{
        border: "1px solid #ccc",
        borderRadius: "8px",
        padding: "1rem",
        marginTop: "1rem",
        backgroundColor: "#f9f9f9",
        maxWidth: "600px",
      }}
    >
      <h2 style={{ marginBottom: "1rem" }}>{compound.Name}</h2>
      <table>
        <tbody>
          <tr>
            <td>
              <strong>Formula:</strong>
            </td>
            <td>{compound.formula || "N/A"}</td>
          </tr>
          <tr>
            <td>
              <strong>Molecular Weight:</strong>
            </td>
            <td>{compound.MW ? `${compound.MW} g/mol` : "N/A"}</td>
          </tr>
          <tr>
            <td>
              <strong>CAS Number:</strong>
            </td>
            <td>{compound.CAS || "N/A"}</td>
          </tr>
          <tr>
            <td>
              <strong>Classification:</strong>
            </td>
            <td>{compound.class || "N/A"}</td>
          </tr>
          <tr>
            <td>
              <strong>SMILES:</strong>
            </td>
            <td style={{ fontFamily: "monospace" }}>
              {compound.SMILES || "N/A"}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};

export default CompoundInfo;
