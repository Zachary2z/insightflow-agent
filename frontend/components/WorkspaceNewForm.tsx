"use client";

import React, { FormEvent, useState } from "react";
import { createWorkspace, type Workspace } from "../lib/api";

type WorkspaceNewFormProps = {
  onCreated?: (workspace: Workspace) => void;
};

export default function WorkspaceNewForm({ onCreated }: WorkspaceNewFormProps) {
  const [name, setName] = useState("");
  const [created, setCreated] = useState<Workspace | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setError("Workspace name is required.");
      return;
    }
    try {
      setIsSubmitting(true);
      setError("");
      const workspace = await createWorkspace(name.trim());
      setCreated(workspace);
      onCreated?.(workspace);
      if (!onCreated && workspace.workspace_id) {
        window.location.assign(`/workspaces/${workspace.workspace_id}/datasets`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create workspace");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="panel">
      <h2>Workspace Details</h2>
      <form className="form-grid" onSubmit={handleSubmit}>
        <label htmlFor="workspace-name">Workspace name</label>
        <input
          id="workspace-name"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Finance analysis"
        />
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating..." : "Create workspace"}
        </button>
      </form>
      {error ? <p role="alert">{error}</p> : null}
      {created ? (
        <p role="status">
          Workspace created: <strong>{created.name}</strong>
        </p>
      ) : null}
    </section>
  );
}
