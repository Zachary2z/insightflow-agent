"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { listWorkspaces, type Workspace } from "../lib/api";

export default function WorkspaceList() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setIsLoading(true);
        const response = await listWorkspaces();
        if (!cancelled) {
          setWorkspaces(response.workspaces ?? []);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load workspaces");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (isLoading) {
    return <p role="status">Loading workspaces</p>;
  }

  if (error) {
    return (
      <section className="panel" role="alert">
        <h2>Workspace Load Failed</h2>
        <p>{error}</p>
      </section>
    );
  }

  if (workspaces.length === 0) {
    return (
      <section className="panel">
        <h2>No Workspaces</h2>
        <p>Create a workspace to import CSV, Excel, or SQLite data.</p>
      </section>
    );
  }

  return (
    <section className="stack">
      {workspaces.map((workspace) => (
        <article className="panel item-row" key={workspace.workspace_id}>
          <div>
            <h2>{workspace.name}</h2>
            <p>{workspace.workspace_id}</p>
            {workspace.updated_at ? <p>Updated {workspace.updated_at}</p> : null}
          </div>
          <Link className="button" href={`/workspaces/${workspace.workspace_id}/datasets`}>
            Open datasets
          </Link>
        </article>
      ))}
    </section>
  );
}
