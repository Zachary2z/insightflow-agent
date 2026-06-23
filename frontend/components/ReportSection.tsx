import React from "react";
import type { WorkspaceReportSection } from "../lib/api";

type ReportSectionProps = {
  section: WorkspaceReportSection;
};

function previewColumns(section: WorkspaceReportSection): string[] {
  if (section.columns?.length) {
    return section.columns;
  }
  const firstRow = section.rows_preview?.[0];
  return firstRow ? Object.keys(firstRow) : [];
}

export default function ReportSection({ section }: ReportSectionProps) {
  const columns = previewColumns(section);
  const rows = section.rows_preview ?? [];

  return (
    <article className="panel stack">
      <header>
        <h3>{section.title}</h3>
        <p>Status: {section.status}</p>
      </header>
      {section.purpose ? <p>{section.purpose}</p> : null}
      {section.question ? (
        <section>
          <h4>Question</h4>
          <p>{section.question}</p>
        </section>
      ) : null}
      {section.summary ? (
        <section>
          <h4>Summary</h4>
          <p>{section.summary}</p>
        </section>
      ) : null}
      {section.error ? (
        <section>
          <h4>Error</h4>
          <p role="alert">{section.error}</p>
        </section>
      ) : null}
      {section.sql ? (
        <section>
          <h4>SQL</h4>
          <pre>{section.sql}</pre>
        </section>
      ) : null}
      {rows.length && columns.length ? (
        <section>
          <h4>Rows Preview</h4>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {columns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {columns.map((column) => (
                      <td key={column}>{String(row[column] ?? "")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
      {section.evidence_notes?.length ? (
        <section>
          <h4>Evidence Notes</h4>
          <ul>
            {section.evidence_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {section.artifact_paths?.length ? (
        <section>
          <h4>Artifacts</h4>
          <ul>
            {section.artifact_paths.map((path) => (
              <li key={path}>{path}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {section.trace_nodes?.length ? (
        <section>
          <h4>Trace Nodes</h4>
          <p>{section.trace_nodes.join(", ")}</p>
        </section>
      ) : null}
      {section.provider_metadata && Object.keys(section.provider_metadata).length ? (
        <section>
          <h4>Provider Metadata</h4>
          <pre>{JSON.stringify(section.provider_metadata, null, 2)}</pre>
        </section>
      ) : null}
    </article>
  );
}
