"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { listWorkspaceReports, type WorkspaceReport } from "../lib/api";

type ReportListProps = {
  workspaceId: string;
};

export default function ReportList({ workspaceId }: ReportListProps) {
  const [reports, setReports] = useState<WorkspaceReport[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isActive = true;
    async function loadReports() {
      try {
        setIsLoading(true);
        setError("");
        const response = await listWorkspaceReports(workspaceId);
        if (isActive) {
          setReports(response.reports);
        }
      } catch (err) {
        if (isActive) {
          setError(err instanceof Error ? err.message : "Unable to load reports");
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }
    loadReports();
    return () => {
      isActive = false;
    };
  }, [workspaceId]);

  if (isLoading) {
    return <p role="status">Loading reports</p>;
  }

  if (error) {
    return <p role="alert">{error}</p>;
  }

  if (!reports.length) {
    return (
      <article className="panel">
        <h2>Reports</h2>
        <p>No reports generated yet.</p>
      </article>
    );
  }

  return (
    <section className="stack">
      <h2>Reports</h2>
      {reports.map((report) => (
        <article className="panel item-row" key={report.report_id}>
          <div>
            <h3>{report.title}</h3>
            <p>Status: {report.status}</p>
            <p>Type: {report.report_type}</p>
            {report.created_at ? <p>Created: {report.created_at}</p> : null}
          </div>
          <Link className="button" href={`/workspaces/${workspaceId}/reports/${report.report_id}`}>
            Open report
          </Link>
        </article>
      ))}
    </section>
  );
}
