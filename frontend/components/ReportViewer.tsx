"use client";

import React, { useEffect, useState } from "react";
import { getWorkspaceReport, type WorkspaceReport } from "../lib/api";
import ReportDownloadLink from "./ReportDownloadLink";
import ReportSection from "./ReportSection";

type ReportViewerProps = {
  workspaceId: string;
  reportId: string;
};

export default function ReportViewer({ workspaceId, reportId }: ReportViewerProps) {
  const [report, setReport] = useState<WorkspaceReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isActive = true;
    async function loadReport() {
      try {
        setIsLoading(true);
        setError("");
        const response = await getWorkspaceReport(workspaceId, reportId);
        if (isActive) {
          setReport(response.report);
        }
      } catch (err) {
        if (isActive) {
          setError(err instanceof Error ? err.message : "Unable to load report");
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }
    loadReport();
    return () => {
      isActive = false;
    };
  }, [workspaceId, reportId]);

  if (isLoading) {
    return <p role="status">Loading report</p>;
  }

  if (error) {
    return <p role="alert">{error}</p>;
  }

  if (!report) {
    return (
      <section className="panel">
        <h2>Report</h2>
        <p>Report was not found.</p>
      </section>
    );
  }

  return (
    <section className="stack">
      <article className="panel stack">
        <div className="item-row">
          <div>
            <h2>{report.title}</h2>
            <p>Status: {report.status}</p>
            <p>Type: {report.report_type}</p>
            <p>Goal: {report.report_goal}</p>
          </div>
          <ReportDownloadLink workspaceId={workspaceId} reportId={report.report_id} />
        </div>
        {report.executive_summary?.length ? (
          <section>
            <h3>Executive Summary</h3>
            <ul>
              {report.executive_summary.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        ) : null}
        <section>
          <h3>Artifact Paths</h3>
          <ul>
            {report.markdown_path ? <li>Markdown: {report.markdown_path}</li> : null}
            {report.json_path ? <li>JSON: {report.json_path}</li> : null}
            {report.trace_path ? <li>Trace: {report.trace_path}</li> : null}
            {report.artifact_dir ? <li>Artifacts: {report.artifact_dir}</li> : null}
          </ul>
        </section>
        {report.provider_metadata && Object.keys(report.provider_metadata).length ? (
          <section>
            <h3>Provider Metadata</h3>
            <pre>{JSON.stringify(report.provider_metadata, null, 2)}</pre>
          </section>
        ) : null}
      </article>
      <section className="stack">
        <h2>Sections</h2>
        {report.sections?.length ? (
          report.sections.map((section) => <ReportSection key={section.section_id} section={section} />)
        ) : (
          <p>No report sections returned.</p>
        )}
      </section>
    </section>
  );
}
