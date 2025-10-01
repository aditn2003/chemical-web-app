import React from "react";

interface ReactivityInfoProps {
  reactivity: {
    chemicalClass?: string;
    oximeReactivity?: string;
    reactiveGroups?: string[];
    steric?: string;
    leavingGroup?: string;
    reactiveScore?: number;
  };
}

const ReactivityInfo: React.FC<ReactivityInfoProps> = ({ reactivity }) => {
  return (
    <div
      style={{
        border: "1px solid #ccc",
        borderRadius: "8px",
        padding: "1rem",
        marginTop: "1.5rem",
        backgroundColor: "#eef5ff",
        maxWidth: "600px",
      }}
    >
      <h3>Reactivity Information</h3>
      <table>
        <tbody>
          <tr>
            <td>
              <strong>Chemical Class:</strong>
            </td>
            <td>{reactivity.chemicalClass || "N/A"}</td>
          </tr>
          <tr>
            <td>
              <strong>Oxime Reactivity:</strong>
            </td>
            <td>{reactivity.oximeReactivity || "N/A"}</td>
          </tr>
          <tr>
            <td>
              <strong>Steric Hindrance:</strong>
            </td>
            <td>{reactivity.steric || "N/A"}</td>
          </tr>
          <tr>
            <td>
              <strong>Leaving Group:</strong>
            </td>
            <td>{reactivity.leavingGroup || "N/A"}</td>
          </tr>
          <tr>
            <td>
              <strong>Reactive Score:</strong>
            </td>
            <td>{reactivity.reactiveScore ?? "N/A"}</td>
          </tr>
          <tr>
            <td>
              <strong>Reactive Groups:</strong>
            </td>
            <td>
              {reactivity.reactiveGroups && reactivity.reactiveGroups.length > 0
                ? reactivity.reactiveGroups.join(", ")
                : "None"}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};

export default ReactivityInfo;
