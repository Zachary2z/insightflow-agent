import React from "react";

type SemanticLayerEditorProps = {
  semanticLayer: {
    metrics?: Array<Record<string, unknown>>;
    dimensions?: Array<Record<string, unknown>>;
    entities?: Array<Record<string, unknown>>;
    time_fields?: Array<Record<string, unknown>>;
  };
};

function displayValue(item: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = item[key];
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      return String(value);
    }
  }
  return "";
}

function renderItems(items: Array<Record<string, unknown>>, detailKeys: string[]) {
  if (items.length === 0) {
    return <p>No items returned.</p>;
  }
  return (
    <ul>
      {items.map((item, index) => {
        const name = displayValue(item, ["name", "field", "key"]) || `item-${index + 1}`;
        const detail = displayValue(item, detailKeys);
        return (
          <li key={`${name}-${index}`}>
            <strong>{name}</strong>
            {detail && detail !== name ? <span>: {detail}</span> : null}
          </li>
        );
      })}
    </ul>
  );
}

export default function SemanticLayerEditor({ semanticLayer }: SemanticLayerEditorProps) {
  return (
    <section className="stack">
      <h2>Semantic Layer</h2>
      <article className="panel">
        <h3>Metrics</h3>
        {renderItems(semanticLayer.metrics ?? [], ["formula", "expression", "field", "table"])}
      </article>
      <article className="panel">
        <h3>Dimensions</h3>
        {renderItems(semanticLayer.dimensions ?? [], ["field", "column", "table"])}
      </article>
      <article className="panel">
        <h3>Entities</h3>
        {renderItems(semanticLayer.entities ?? [], ["key", "field", "table"])}
      </article>
      <article className="panel">
        <h3>Time Fields</h3>
        {renderItems(semanticLayer.time_fields ?? [], ["field", "table"])}
      </article>
    </section>
  );
}
