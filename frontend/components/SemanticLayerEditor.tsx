import React from "react";
import ProductCard from "./ProductCard";

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
    return <p>暂无建议项。</p>;
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
      <h2>语义层草稿结果</h2>
      <ProductCard>
        <h3>指标</h3>
        {renderItems(semanticLayer.metrics ?? [], ["formula", "expression", "field", "table"])}
      </ProductCard>
      <ProductCard>
        <h3>维度</h3>
        {renderItems(semanticLayer.dimensions ?? [], ["field", "column", "table"])}
      </ProductCard>
      <ProductCard>
        <h3>实体</h3>
        {renderItems(semanticLayer.entities ?? [], ["key", "field", "table"])}
      </ProductCard>
      <ProductCard>
        <h3>时间字段</h3>
        {renderItems(semanticLayer.time_fields ?? [], ["field", "table"])}
      </ProductCard>
    </section>
  );
}
