"use client";

import React, { FormEvent, useEffect, useState } from "react";
import { importSqliteSource, listSources, uploadSource, type WorkspaceSource } from "../lib/api";

type DatasetManagerProps = {
  workspaceId: string;
};

export default function DatasetManager({ workspaceId }: DatasetManagerProps) {
  const [sources, setSources] = useState<WorkspaceSource[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sqlitePath, setSqlitePath] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  async function refreshSources() {
    const response = await listSources(workspaceId);
    setSources(response.sources ?? []);
  }

  useEffect(() => {
    refreshSources().catch((err) => setError(err instanceof Error ? err.message : "Unable to load sources"));
  }, [workspaceId]);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      setError("Choose a CSV or Excel file first.");
      return;
    }
    try {
      setIsBusy(true);
      setError("");
      const response = await uploadSource(workspaceId, selectedFile);
      setStatus(`Imported tables: ${(response.imported_tables ?? []).join(", ")}`);
      await refreshSources();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to upload source");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleSqlite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sqlitePath.trim()) {
      setError("SQLite file path is required.");
      return;
    }
    try {
      setIsBusy(true);
      setError("");
      const response = await importSqliteSource(workspaceId, sqlitePath.trim());
      setStatus(`Imported tables: ${(response.imported_tables ?? []).join(", ")}`);
      setSqlitePath("");
      await refreshSources();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to import SQLite source");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="stack">
      <article className="panel">
        <h2>Upload File</h2>
        <form className="form-grid" onSubmit={handleUpload}>
          <label htmlFor="source-file">CSV or Excel file</label>
          <input
            id="source-file"
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
          <button type="submit" disabled={isBusy}>
            Upload source
          </button>
        </form>
      </article>
      <article className="panel">
        <h2>SQLite Source</h2>
        <form className="form-grid" onSubmit={handleSqlite}>
          <label htmlFor="sqlite-path">SQLite file path</label>
          <input
            id="sqlite-path"
            type="text"
            value={sqlitePath}
            onChange={(event) => setSqlitePath(event.target.value)}
            placeholder="/absolute/path/to/source.db"
          />
          <button type="submit" disabled={isBusy}>
            Import SQLite
          </button>
        </form>
      </article>
      {status ? <p role="status">{status}</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      <article className="panel">
        <h2>Imported Sources</h2>
        {sources.length === 0 ? (
          <p>No sources imported yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Imported tables</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((source, index) => (
                  <tr key={source.source_id ?? `${source.name}-${index}`}>
                    <td>{source.name ?? "Unnamed source"}</td>
                    <td>{source.source_type ?? "source"}</td>
                    <td>{(source.imported_tables ?? []).join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </section>
  );
}
