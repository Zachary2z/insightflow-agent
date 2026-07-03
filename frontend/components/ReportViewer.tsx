"use client";

import React, { useEffect, useState } from "react";
import {
  getWorkspaceArtifactUrl,
  getWorkspaceReport,
  resolveApiUrl,
  type WorkspaceReport,
} from "../lib/api";
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
    generatedAtPrefix: "生成时间",
    timeRangePrefix: "时间范围",
    dataSourcesPrefix: "数据来源",
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
    generatedAtPrefix: "Generated",
    timeRangePrefix: "Time range",
    dataSourcesPrefix: "Data sources",
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

function ReportDocumentBody({
  report,
  language,
  workspaceId,
}: {
  report: WorkspaceReport;
  language: ReportLanguage;
  workspaceId: string;
}) {
  const labels = REPORT_LABELS[language];
  const document = report.document;
  const sections = document?.sections ?? [];
  const evidenceTables = report.evidence_pack?.tables ?? [];
  const evidenceCharts = report.evidence_pack?.charts ?? [];
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
          <SectionCharts
            charts={chartsForSection(evidenceCharts, section.section_id, section.chart_refs ?? [])}
            workspaceId={workspaceId}
          />
          <SectionEvidenceTables
            tables={evidenceTables.filter((table) => table.source_chapter_id === section.section_id)}
          />
        </ProductCard>
      ))}
    </section>
  );
}

function SectionCharts({ charts, workspaceId }: { charts: Array<Record<string, unknown>>; workspaceId: string }) {
  if (!charts.length) {
    return null;
  }
  return (
    <div className="report-section-charts">
      {charts.map((chart, index) => {
        const title = textValue(chart.title, "报告图表");
        const description = textValue(chart.description, "建议基于本章节证据生成图表后再用于汇报展示。");
        const url = chartArtifactUrl(chart, workspaceId);
        if (!url) {
          return (
            <div className="report-chart-intent" key={`${title}-${index}`}>
              <strong>待生成图表：{title}</strong>
              <p>{description}</p>
            </div>
          );
        }
        return (
          <figure className="report-chart-artifact" key={`${title}-${index}`}>
            <img src={url} alt={title} />
            <figcaption>
              <strong>{title}</strong>
              {description ? <span>{description}</span> : null}
              <a className="secondary-button" href={url} download>
                下载图表
              </a>
            </figcaption>
          </figure>
        );
      })}
    </div>
  );
}

function SectionEvidenceTables({ tables }: { tables: Array<Record<string, unknown>> }) {
  const visibleTables = tables.filter((table) => {
    const rows = Array.isArray(table.rows) ? table.rows : [];
    return rows.length > 0;
  });
  if (!visibleTables.length) {
    return null;
  }
  return (
    <div className="report-evidence-tables">
      {visibleTables.map((table, index) => {
        const title = typeof table.title === "string" ? table.title : "证据表";
        const description = typeof table.description === "string" ? table.description : "";
        const columns = Array.isArray(table.columns) ? table.columns.map(String) : [];
        const rows = Array.isArray(table.rows) ? table.rows.slice(0, 5) : [];
        return (
          <div className="report-evidence-table" key={`${title}-${index}`}>
            <h4>{title}</h4>
            {description ? <p>{description}</p> : null}
            {columns.length ? (
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
                        <td key={column}>{cellValue(row, column)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function chartsForSection(charts: Array<Record<string, unknown>>, sectionId: string, chartRefs: string[]) {
  const refs = new Set(chartRefs);
  const selected = charts.filter((chart) => {
    const chartId = typeof chart.chart_id === "string" ? chart.chart_id : "";
    return chart.source_chapter_id === sectionId || refs.has(chartId);
  });
  const unique = new Map<string, Record<string, unknown>>();
  selected.forEach((chart, index) => {
    const key = typeof chart.chart_id === "string" && chart.chart_id ? chart.chart_id : `${textValue(chart.title, "")}-${index}`;
    unique.set(key, chart);
  });
  return Array.from(unique.values());
}

function chartArtifactUrl(chart: Record<string, unknown>, workspaceId: string) {
  const url = textValue(chart.url, "");
  if (url) {
    return resolveApiUrl(url);
  }
  const path = textValue(chart.path, "");
  if (!path) {
    return "";
  }
  if (/^https?:\/\//.test(path) || path.startsWith("/api/")) {
    return resolveApiUrl(path);
  }
  if (path.startsWith("/")) {
    return "";
  }
  return getWorkspaceArtifactUrl(workspaceId, path);
}

function textValue(value: unknown, fallback: string) {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function cellValue(row: unknown, column: string) {
  if (row && typeof row === "object" && !Array.isArray(row)) {
    const value = (row as Record<string, unknown>)[column];
    return value == null ? "" : String(value);
  }
  return "";
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
              <span>{metaText(labels.generatedAtPrefix, formatReportDate(report.updated_at || report.created_at), language)}</span>
              <span>{metaText(labels.timeRangePrefix, report.document?.time_range || "当前工作区可用数据", language)}</span>
              <span>{metaText(labels.dataSourcesPrefix, joinText(report.document?.data_sources), language)}</span>
            </div>
          </div>
          <ReportDownloadLink workspaceId={workspaceId} reportId={report.report_id} label={labels.downloadMarkdown} />
        </div>
        {report.document?.opening_summary ? (
          <section className="report-summary">
            <h3>{labels.openingSummary}</h3>
            <p>{report.document.opening_summary}</p>
          </section>
        ) : null}
      </ProductCard>
      <ReportDocumentBody report={report} language={language} workspaceId={workspaceId} />
      <TextList title={labels.actionRecommendations} items={report.document?.action_recommendations} />
      <TextList title={labels.dataBoundaries} items={report.document?.data_boundaries} />
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

function metaText(label: string, value: string, language: ReportLanguage) {
  return `${label}${language === "zh" ? "：" : ": "}${value}`;
}

function formatReportDate(value?: string) {
  return value ? value.slice(0, 10) : "未知";
}

function joinText(items?: string[]) {
  const visible = items?.filter((item) => item.trim()) ?? [];
  return visible.length ? visible.join("、") : "当前工作区数据";
}
