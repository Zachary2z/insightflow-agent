import React from "react";

type SemanticLayerEditorProps = {
  semanticLayer: {
    metrics?: Array<{ name: string; expression?: string; table?: string }>;
    dimensions?: Array<{ name: string; column?: string; table?: string }>;
  };
};

export default function SemanticLayerEditor({ semanticLayer }: SemanticLayerEditorProps) {
  return (
    <section>
      <h2>Semantic Layer</h2>
      <article className="panel">
        <h3>Metrics</h3>
        <ul>
          {(semanticLayer.metrics ?? []).map((metric) => (
            <li key={metric.name}>
              {metric.name}
              {metric.expression ? `: ${metric.expression}` : ""}
            </li>
          ))}
        </ul>
      </article>
      <article className="panel">
        <h3>Dimensions</h3>
        <ul>
          {(semanticLayer.dimensions ?? []).map((dimension) => (
            <li key={dimension.name}>
              {dimension.name}
              {dimension.column ? `: ${dimension.column}` : ""}
            </li>
          ))}
        </ul>
      </article>
    </section>
  );
}
