import React from "react";
import type { EvidenceSummary } from "../lib/api";

type EvidencePanelProps = {
  evidence?: EvidenceSummary;
};

function cellValue(row: unknown[] | Record<string, unknown>, column: string, index: number) {
  if (Array.isArray(row)) {
    return row[index];
  }
  return row[column];
}

export default function EvidencePanel({ evidence }: EvidencePanelProps) {
  const tablePreview = evidence?.table_preview;
  const columns = tablePreview?.columns ?? [];
  const rows = (tablePreview?.rows ?? []) as Array<unknown[] | Record<string, unknown>>;
  const notes = evidence?.evidence_notes?.filter((note) => note.trim()) ?? [];

  return (
    <article className="panel evidence-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Evidence</p>
          <h3>证据表</h3>
        </div>
        {evidence?.validation_status ? <span className="status-chip">{evidence.validation_status}</span> : null}
      </div>
      {columns.length && rows.length ? (
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
                  {columns.map((column, index) => (
                    <td key={column}>{String(cellValue(row, column, index) ?? "")}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>暂无证据表预览。</p>
      )}
      {notes.length ? (
        <ul className="compact-list">
          {notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}
