import Plot from "react-plotly.js";

export default function AeglGraph({
  absorptionGraph,
  fluxGraph,
}: {
  absorptionGraph: string;
  fluxGraph: string;
}) {
  const abs = JSON.parse(absorptionGraph);
  const flux = JSON.parse(fluxGraph);

  return (
    <div>
      <div style={{ marginBottom: "1rem" }}>
        <h5 style={{ fontSize: "0.9rem", marginBottom: "0.5rem" }}>
          AEGL Dermal Absorption
        </h5>
        <Plot
          data={abs.data}
          layout={{ ...abs.layout, autosize: true }}
          useResizeHandler
          style={{ width: "100%", height: "300px" }}
        />
      </div>

      <div>
        <h5 style={{ fontSize: "0.9rem", marginBottom: "0.5rem" }}>
          AEGL Flux vs Time
        </h5>
        <Plot
          data={flux.data}
          layout={{ ...flux.layout, autosize: true }}
          useResizeHandler
          style={{ width: "100%", height: "300px" }}
        />
      </div>
    </div>
  );
}
