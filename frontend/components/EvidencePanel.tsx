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

function compactLedgerFact(item: Record<string, unknown>) {
  const label = typeof item.label === "string" ? item.label : typeof item.metric_id === "string" ? item.metric_id : "";
  const value = item.value;
  if (!label || value === undefined || value === null || typeof value === "object") {
    return "";
  }
  return `${label}: ${String(value)}`;
}

function isInternalColumn(column: string) {
  return ["task_id", "task_purpose"].includes(column.trim().toLowerCase());
}

export default function EvidencePanel({ evidence }: EvidencePanelProps) {
  const tablePreview = evidence?.table_preview;
  const rawColumns = tablePreview?.columns ?? [];
  const visibleColumnIndexes = rawColumns.map((column, index) => ({ column, index })).filter((item) => !isInternalColumn(item.column));
  const columns = visibleColumnIndexes.map((item) => item.column);
  const rows = (tablePreview?.rows ?? []) as Array<unknown[] | Record<string, unknown>>;
  const notes = evidence?.evidence_notes?.filter((note) => note.trim()) ?? [];
  const ledger = evidence?.ledger_summary;
  const taskGroups = (ledger?.task_groups ?? []).filter((group) => group.title || group.facts?.length);
  const ledgerFacts = [
    ...(ledger?.facts ?? []).map(compactLedgerFact),
    ...(ledger?.derived_metrics ?? []).map(compactLedgerFact),
  ].filter(Boolean);
  const businessLimits = ledger?.business_data_limits?.length ? ledger.business_data_limits : ledger?.data_limits ?? [];

  return (
    <article className="panel evidence-panel">
      <div className="section-heading">
        <div>
          <p className="product-eyebrow">Evidence</p>
          <h3>证据表</h3>
          <p className="panel-help">用于支撑业务结论的结果预览。</p>
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
                  {visibleColumnIndexes.map(({ column, index }) => (
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
      {ledger ? (
        <section className="ledger-summary" aria-label="证据摘要">
          <h4>证据摘要</h4>
          <div className="ledger-summary-grid">
            {ledger.confidence ? (
              <span>
                置信度：<strong>{ledger.confidence}</strong>
              </span>
            ) : null}
          </div>
          {ledger.time_policy_note ? <p>{ledger.time_policy_note}</p> : null}
          {taskGroups.length ? (
            <div className="ledger-task-groups">
              {taskGroups.map((group, index) => (
                <section className="ledger-task-group" key={`${group.title || "业务证据"}-${index}`}>
                  <div className="ledger-task-heading">
                    <strong>{group.title || "业务证据"}</strong>
                    {group.status ? <span>{group.status}</span> : null}
                  </div>
                  {group.facts?.length ? (
                    <ul className="compact-list">
                      {group.facts.slice(0, 4).map((fact) => (
                        <li key={fact}>{fact}</li>
                      ))}
                    </ul>
                  ) : null}
                </section>
              ))}
            </div>
          ) : ledgerFacts.length ? (
            <ul className="compact-list">
              {ledgerFacts.slice(0, 4).map((fact) => (
                <li key={fact}>{fact}</li>
              ))}
            </ul>
          ) : null}
          {businessLimits.length ? (
            <ul className="compact-list">
              {businessLimits.slice(0, 3).map((limit) => (
                <li key={limit}>{limit}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}
    </article>
  );
}
