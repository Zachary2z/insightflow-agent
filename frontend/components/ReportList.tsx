"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { listWorkspaceReports, type WorkspaceReport } from "../lib/api";
import ProductCard from "./ProductCard";
import { StatusPill } from "./ProductStatus";

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
    return <p role="status">正在加载报告…</p>;
  }

  if (error) {
    return <p role="alert">{error}</p>;
  }

  if (!reports.length) {
    return (
      <ProductCard className="report-list-card">
        <div className="product-section-title">
          <div>
            <p className="product-eyebrow">报告库</p>
            <h2>报告列表</h2>
          </div>
        </div>
        <div className="dataset-empty-state">
          <h3>还没有生成报告</h3>
          <p>生成第一份管理层复盘，之后会在这里按创建时间展示。</p>
        </div>
      </ProductCard>
    );
  }

  return (
    <ProductCard className="report-list-card">
      <div className="product-section-title">
        <div>
          <p className="product-eyebrow">报告库</p>
          <h2>报告列表</h2>
          <p className="panel-help">按创建时间查看已生成报告，打开后可阅读正文、图表和技术附录。</p>
        </div>
      </div>
      <div className="report-list">
      {reports.map((report) => (
        <article className="report-list-item" key={report.report_id}>
          <div>
            <h3>{report.title}</h3>
            <div className="report-meta-row">
              <StatusPill tone={statusTone(report.status)}>生成状态：{statusLabel(report.status)}</StatusPill>
              <span>时间范围：{reportTimeRange(report)}</span>
              <span>更新时间：{formatReportDate(report.updated_at || report.created_at)}</span>
            </div>
            <p className="panel-help">摘要：{reportSummary(report)}</p>
          </div>
          <Link className="button" href={`/workspaces/${workspaceId}/reports/${report.report_id}`}>
            打开报告
          </Link>
        </article>
      ))}
      </div>
    </ProductCard>
  );
}

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

function statusTone(status: string): "green" | "orange" | "red" | "blue" | "neutral" {
  if (status === "completed") {
    return "green";
  }
  if (status === "failed") {
    return "red";
  }
  if (status === "partial") {
    return "orange";
  }
  if (status === "running") {
    return "blue";
  }
  return "neutral";
}

function formatReportDate(value?: string) {
  if (!value) {
    return "未知";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function reportTimeRange(report: WorkspaceReport) {
  return report.document?.time_range || report.plan?.time_range || "当前工作区可用数据";
}

function reportSummary(report: WorkspaceReport) {
  return (
    report.document?.opening_summary ||
    "打开报告查看正文、图表和行动建议。"
  );
}
