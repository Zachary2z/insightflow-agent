"use client";

import React, { useState } from "react";
import { createSemanticDraft, type SemanticLayer } from "../lib/api";
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
      setError(err instanceof Error ? err.message : "Unable to draft semantic layer");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="stack">
      <article className="panel action-panel">
        <div>
          <h2>Draft Semantic Layer</h2>
          <p>Create metric, dimension, entity, and time-field suggestions from the profile.</p>
        </div>
        <button type="button" onClick={handleDraft} disabled={isLoading}>
          {isLoading ? "Drafting..." : "Draft semantic layer"}
        </button>
      </article>
      {error ? <p role="alert">{error}</p> : null}
      {semanticLayer ? <SemanticLayerEditor semanticLayer={semanticLayer} /> : null}
    </section>
  );
}
