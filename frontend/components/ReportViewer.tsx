"use client";

import React, { useEffect, useState } from "react";
import { getWorkspaceReport, type WorkspaceReport } from "../lib/api";
import ReportDownloadLink from "./ReportDownloadLink";
import ReportSection from "./ReportSection";
import ReportTechnicalAppendix from "./ReportTechnicalAppendix";

type ReportViewerProps = {
  workspaceId: string;
  reportId: string;
};

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    completed: "已完成",
    partial: "部分完成",
    failed: "失败",
    running: "生成中",
    draft: "草稿",
  };
  return labels[status] ?? status;
}

function progressSummary(report: WorkspaceReport) {
  const sections = report.sections ?? [];
  const total = sections.length;
  const completed = sections.filter((section) => section.status === "completed").length;
  const failed = sections.filter((section) => section.status === "failed").length;
  const running = sections.filter((section) => section.status === "running").length;
  const parts = [`进度：${completed}/${total} 个章节已完成`];
  if (failed > 0) {
    parts.push(`${failed} 个章节失败`);
  }
  if (running > 0 || report.status === "running") {
    parts.push("仍在生成");
  }
  return parts.join("，");
}

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
            <p>状态：{statusLabel(report.status)}</p>
            <p>{progressSummary(report)}</p>
            <p>类型：{report.report_type}</p>
            <p>目标：{report.report_goal}</p>
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
      </article>
      <section className="stack">
        <h2>业务章节</h2>
        {report.sections?.length ? (
          report.sections.map((section) => <ReportSection key={section.section_id} section={section} />)
        ) : (
          <p>No report sections returned.</p>
        )}
      </section>
      <ReportTechnicalAppendix report={report} />
    </section>
  );
}
