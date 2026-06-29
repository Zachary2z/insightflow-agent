"use client";

import React, { useEffect, useState } from "react";
import { getWorkspaceReport, type WorkspaceReport } from "../lib/api";
import ProductCard from "./ProductCard";
import { StatusPill } from "./ProductStatus";
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
    return <p role="status">正在加载报告</p>;
  }

  if (error) {
    return <p role="alert">{error}</p>;
  }

  if (!report) {
    return (
      <ProductCard>
        <h2>报告不存在</h2>
        <p>没有找到这份报告。</p>
      </ProductCard>
    );
  }

  return (
    <section className="report-viewer">
      <ProductCard className="report-reader-hero">
        <div className="report-reader-head">
          <div>
            <p className="product-eyebrow">Report</p>
            <h2>{report.title}</h2>
            <div className="report-meta-row">
              <StatusPill tone={statusTone(report.status)}>生成状态：{statusLabel(report.status)}</StatusPill>
              <span>{progressSummary(report)}</span>
              <span>报告类型：{reportTypeLabel(report.report_type)}</span>
            </div>
            {report.report_goal ? <p className="report-goal-copy">报告目标：{report.report_goal}</p> : null}
          </div>
          <ReportDownloadLink workspaceId={workspaceId} reportId={report.report_id} />
        </div>
        {report.executive_summary?.length ? (
          <section className="report-summary">
            <h3>管理层摘要 / Executive Summary</h3>
            <ul>
              {report.executive_summary.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        ) : null}
      </ProductCard>
      <section className="report-sections">
        <div className="product-section-title">
          <div>
            <p className="product-eyebrow">Sections</p>
            <h2>报告章节</h2>
          </div>
        </div>
        {report.sections?.length ? (
          report.sections.map((section) => (
            <ReportSection
              key={section.section_id}
              section={section}
              workspaceId={workspaceId}
              reportId={report.report_id}
            />
          ))
        ) : (
          <ProductCard>
            <p>暂无报告章节。</p>
          </ProductCard>
        )}
      </section>
      <ReportTechnicalAppendix report={report} />
    </section>
  );
}

function statusTone(status: string): "green" | "orange" | "blue" | "neutral" {
  if (status === "completed") {
    return "green";
  }
  if (status === "failed" || status === "partial") {
    return "orange";
  }
  if (status === "running") {
    return "blue";
  }
  return "neutral";
}

function reportTypeLabel(reportType: string) {
  const labels: Record<string, string> = {
    business_review: "经营复盘",
    channel_performance: "渠道表现",
    revenue_trend: "收入趋势",
  };
  return labels[reportType] ?? reportType;
}
