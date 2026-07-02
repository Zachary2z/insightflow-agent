"use client";

import React, { useEffect, useState } from "react";
import { getWorkspaceReport, type WorkspaceReport } from "../lib/api";
import ProductCard from "./ProductCard";
import { StatusPill } from "./ProductStatus";
import ReportDownloadLink from "./ReportDownloadLink";
import ReportTechnicalAppendix from "./ReportTechnicalAppendix";

type ReportViewerProps = {
  workspaceId: string;
  reportId: string;
};

type ReportLanguage = "zh" | "en";

const REPORT_LABELS = {
  zh: {
    eyebrow: "报告",
    statusPrefix: "生成状态",
    progressPrefix: "进度",
    progressComplete: "个章节已完成",
    progressRunning: "仍在生成",
    reportTypePrefix: "报告类型",
    reportGoalPrefix: "报告目标",
    openingSummary: "开篇摘要",
    bodyEyebrow: "正文",
    reportBody: "报告正文",
    actionRecommendations: "行动建议",
    dataBoundaries: "数据边界",
    emptyBody: "暂无报告正文。",
    missingTitle: "报告不存在",
    missingBody: "没有找到这份报告。",
    downloadMarkdown: "下载 Markdown",
  },
  en: {
    eyebrow: "Report",
    statusPrefix: "Status",
    progressPrefix: "Progress",
    progressComplete: "sections complete",
    progressRunning: "still running",
    reportTypePrefix: "Report type",
    reportGoalPrefix: "Report goal",
    openingSummary: "Opening Summary",
    bodyEyebrow: "Body",
    reportBody: "Report Body",
    actionRecommendations: "Action Recommendations",
    dataBoundaries: "Data Boundaries",
    emptyBody: "No report body yet.",
    missingTitle: "Report not found",
    missingBody: "This report could not be found.",
    downloadMarkdown: "Download Markdown",
  },
} as const;

function reportLanguage(report: WorkspaceReport): ReportLanguage {
  const text = [
    report.report_goal,
    report.document?.opening_summary ?? "",
    ...(report.document?.sections?.map((section) => `${section.title}\n${section.body}`) ?? []),
    ...(report.document?.action_recommendations ?? []),
    ...(report.document?.data_boundaries ?? []),
    ...(report.executive_summary ?? []),
    ...(report.key_findings ?? []),
    ...(report.action_priorities ?? []),
    ...(report.chart_and_evidence ?? []),
    ...(report.risks_and_limits ?? []),
  ].join("\n");
  return /[\u4e00-\u9fff]/.test(text) ? "zh" : "en";
}

function statusLabel(status: string, language: ReportLanguage) {
  const labels: Record<ReportLanguage, Record<string, string>> = {
    zh: {
      completed: "已完成",
      partial: "部分完成",
      failed: "失败",
      running: "生成中",
      draft: "草稿",
    },
    en: {
      completed: "Completed",
      partial: "Partial",
      failed: "Failed",
      running: "Running",
      draft: "Draft",
    },
  };
  return labels[language][status] ?? status;
}

function progressSummary(report: WorkspaceReport, language: ReportLanguage) {
  const sections = report.document?.sections ?? [];
  const total = sections.length;
  const completed = report.status === "completed" ? total : 0;
  const labels = REPORT_LABELS[language];
  const parts = [
    language === "zh"
      ? `${labels.progressPrefix}：${completed}/${total} ${labels.progressComplete}`
      : `${labels.progressPrefix}: ${completed}/${total} ${labels.progressComplete}`,
  ];
  if (report.status === "running") {
    parts.push(labels.progressRunning);
  }
  return parts.join(language === "zh" ? "，" : ", ");
}

function TextList({ title, items }: { title: string; items?: string[] }) {
  const visibleItems = items?.filter((item) => item.trim()) ?? [];
  if (!visibleItems.length) {
    return null;
  }
  return (
    <section className="report-summary">
      <h3>{title}</h3>
      <ul>
        {visibleItems.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function ReportDocumentBody({ report, language }: { report: WorkspaceReport; language: ReportLanguage }) {
  const labels = REPORT_LABELS[language];
  const document = report.document;
  const sections = document?.sections ?? [];
  if (!sections.length) {
    return (
      <ProductCard>
        <p>{labels.emptyBody}</p>
      </ProductCard>
    );
  }
  return (
    <section className="report-sections">
      <div className="product-section-title">
        <div>
          <p className="product-eyebrow">{labels.bodyEyebrow}</p>
          <h2>{labels.reportBody}</h2>
        </div>
      </div>
      {sections.map((section) => (
        <ProductCard key={section.section_id} className="report-section-card">
          <h3>{section.title}</h3>
          <p>{section.body}</p>
        </ProductCard>
      ))}
    </section>
  );
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
    const labels = REPORT_LABELS.zh;
    return (
      <ProductCard>
        <h2>{labels.missingTitle}</h2>
        <p>{labels.missingBody}</p>
      </ProductCard>
    );
  }

  const language = reportLanguage(report);
  const labels = REPORT_LABELS[language];

  return (
    <section className="report-viewer">
      <ProductCard className="report-reader-hero">
        <div className="report-reader-head">
          <div>
            <p className="product-eyebrow">{labels.eyebrow}</p>
            <h2>{report.title}</h2>
            <div className="report-meta-row">
              <StatusPill tone={statusTone(report.status)}>
                {labels.statusPrefix}
                {language === "zh" ? "：" : ": "}
                {statusLabel(report.status, language)}
              </StatusPill>
              <span>{progressSummary(report, language)}</span>
              <span>
                {labels.reportTypePrefix}
                {language === "zh" ? "：" : ": "}
                {reportTypeLabel(report.report_type, language)}
              </span>
            </div>
            {report.report_goal ? (
              <p className="report-goal-copy">
                {labels.reportGoalPrefix}
                {language === "zh" ? "：" : ": "}
                {report.report_goal}
              </p>
            ) : null}
          </div>
          <ReportDownloadLink workspaceId={workspaceId} reportId={report.report_id} label={labels.downloadMarkdown} />
        </div>
        {report.document?.opening_summary ? (
          <section className="report-summary">
            <h3>{labels.openingSummary}</h3>
            <p>{report.document.opening_summary}</p>
          </section>
        ) : null}
        <TextList title={labels.actionRecommendations} items={report.document?.action_recommendations} />
        <TextList title={labels.dataBoundaries} items={report.document?.data_boundaries} />
      </ProductCard>
      <ReportDocumentBody report={report} language={language} />
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

function reportTypeLabel(reportType: string, language: ReportLanguage) {
  const labels: Record<ReportLanguage, Record<string, string>> = {
    zh: {
      business_review: "经营复盘",
      channel_performance: "渠道表现",
      revenue_trend: "收入趋势",
    },
    en: {
      business_review: "经营复盘",
      channel_performance: "渠道表现",
      revenue_trend: "收入趋势",
    },
  };
  return labels[language][reportType] ?? reportType;
}
