"use client";

import React, { useState } from "react";
import type { WorkspaceReport, WorkspaceReportSection } from "../lib/api";

type ReportTechnicalAppendixProps = {
  report: WorkspaceReport;
};

function hasValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  if (value && typeof value === "object") {
    return Object.keys(value).length > 0;
  }
  return typeof value === "string" ? value.trim().length > 0 : Boolean(value);
}

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  if (!hasValue(value)) {
    return null;
  }
  return (
    <div className="technical-block">
      <h4>{title}</h4>
      <pre>{typeof value === "string" ? value : JSON.stringify(value, null, 2)}</pre>
    </div>
  );
}

function sectionDetails(section: WorkspaceReportSection) {
  return {
    internal_question: section.technical_details?.internal_question ?? section.question,
    purpose: section.technical_details?.purpose ?? section.purpose,
    sql: section.technical_details?.sql ?? section.sql,
    columns: section.technical_details?.columns ?? section.columns,
    rows_preview: section.technical_details?.rows_preview ?? section.rows_preview,
    provider_metadata: section.technical_details?.provider_metadata ?? section.provider_metadata,
    trace_nodes: section.technical_details?.trace_nodes ?? section.trace_nodes,
    trace_path: section.technical_details?.trace_path,
    workspace_run_dir: section.technical_details?.workspace_run_dir,
    error: section.technical_details?.error ?? section.error,
  };
}

function SectionTechnicalDetails({ section }: { section: WorkspaceReportSection }) {
  const details = sectionDetails(section);

  return (
    <article className="technical-block">
      <h3>{section.title}</h3>
      <JsonBlock title="Internal question" value={details.internal_question} />
      <JsonBlock title="Purpose" value={details.purpose} />
      <JsonBlock title="SQL" value={details.sql} />
      <JsonBlock title="Rows preview" value={details.rows_preview} />
      <JsonBlock title="Provider metadata" value={details.provider_metadata} />
      <JsonBlock title="Trace nodes" value={details.trace_nodes} />
      <JsonBlock title="Trace path" value={details.trace_path} />
      <JsonBlock title="Workspace run directory" value={details.workspace_run_dir} />
      <JsonBlock title="Error" value={details.error} />
    </article>
  );
}

export default function ReportTechnicalAppendix({ report }: ReportTechnicalAppendixProps) {
  const [isOpen, setIsOpen] = useState(false);
  const sections = report.sections ?? [];

  return (
    <details className="technical-details">
      <summary onClick={() => setIsOpen((current) => !current)}>技术附录</summary>
      {isOpen ? (
        <div className="technical-content">
          <section className="technical-block">
            <h3>报告元数据</h3>
            <JsonBlock title="Report ID" value={report.report_id} />
            <JsonBlock title="Workspace ID" value={report.workspace_id} />
            <JsonBlock title="JSON path" value={report.json_path} />
            <JsonBlock title="Markdown path" value={report.markdown_path} />
            <JsonBlock title="Trace path" value={report.trace_path} />
            <JsonBlock title="Artifact directory" value={report.artifact_dir} />
            <JsonBlock title="Provider metadata" value={report.provider_metadata} />
          </section>
          {sections.length ? (
            sections.map((section) => (
              <SectionTechnicalDetails key={section.section_id} section={section} />
            ))
          ) : (
            <p>暂无章节技术细节。</p>
          )}
        </div>
      ) : null}
    </details>
  );
}
