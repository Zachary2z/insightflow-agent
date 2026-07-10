"use client";

import React, { useState } from "react";
import { createSemanticDraft, type SemanticLayer } from "../lib/api";
import ProductCard from "./ProductCard";
import SemanticLayerEditor from "./SemanticLayerEditor";

type SemanticLayerWorkspaceProps = {
  workspaceId: string;
};

export default function SemanticLayerWorkspace({ workspaceId }: SemanticLayerWorkspaceProps) {
  const [semanticLayer, setSemanticLayer] = useState<SemanticLayer | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleDraft() {
    try {
      setIsLoading(true);
      setError("");
      const response = await createSemanticDraft(workspaceId);
      setSemanticLayer(response.semantic_layer);
    } catch (err) {
      setError(err instanceof Error ? err.message : "语义层草稿生成失败");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="stack">
      <ProductCard className="action-panel">
        <div>
          <p className="product-eyebrow">业务语义</p>
          <h2>生成语义层草稿</h2>
          <p className="panel-help">根据字段画像生成指标、维度、实体和时间字段建议。</p>
        </div>
        <button type="button" onClick={handleDraft} disabled={isLoading}>
          {isLoading ? "生成中…" : "生成语义层草稿"}
        </button>
      </ProductCard>
      {error ? <p role="alert">{error}</p> : null}
      {semanticLayer ? <SemanticLayerEditor semanticLayer={semanticLayer} /> : null}
    </section>
  );
}
