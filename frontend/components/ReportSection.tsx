import React from "react";
import { getWorkspaceArtifactUrl, resolveApiUrl, type WorkspaceReportSection } from "../lib/api";
import ProductCard from "./ProductCard";
import { StatusPill } from "./ProductStatus";

type ReportSectionProps = {
  section: WorkspaceReportSection;
  workspaceId: string;
  reportId: string;
  language?: "zh" | "en";
};

type ReportBusinessArtifact = NonNullable<WorkspaceReportSection["business_artifacts"]>[number];

const BUSINESS_ANSWER_KEYS = [
  "headline",
  "direct_answer",
  "why",
  "evidence_bullets",
  "recommendations",
  "caveats",
  "confidence",
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function isBusinessAnswer(value: unknown): value is WorkspaceReportSection["business_answer"] {
  if (!isRecord(value)) {
    return false;
  }
  const keys = Object.keys(value).sort();
  if (keys.length !== BUSINESS_ANSWER_KEYS.length || keys.join("|") !== [...BUSINESS_ANSWER_KEYS].sort().join("|")) {
    return false;
  }
  return (
    typeof value.headline === "string" &&
    value.headline.trim().length > 0 &&
    typeof value.direct_answer === "string" &&
    value.direct_answer.trim().length > 0 &&
    typeof value.why === "string" &&
    value.why.trim().length > 0 &&
    Array.isArray(value.evidence_bullets) &&
    Array.isArray(value.recommendations) &&
    Array.isArray(value.caveats) &&
    ["low", "medium", "high"].includes(String(value.confidence))
  );
}

const SECTION_LABELS = {
  zh: {
    sectionStatus: "章节状态",
    conclusion: "结论",
    directAnswer: "直接回答",
    why: "为什么",
    keyEvidence: "关键证据",
    recommendedActions: "建议动作",
    limits: "限制说明",
    confidence: "置信度",
    confidencePrefix: "置信度",
    malformedTitle: "报告章节结构异常",
    malformedBody: "后端没有返回完整的 P16 business_answer，请重新生成报告。",
    chartsAndEvidence: "图表或附件",
    chartAlt: "报告图表",
    unit: "单位",
    downloadChart: "下载图表",
    chartGenerated: "图表已生成",
  },
  en: {
    sectionStatus: "Section status",
    conclusion: "Conclusion",
    directAnswer: "Direct Answer",
    why: "Why",
    keyEvidence: "Key Evidence",
    recommendedActions: "Recommended Actions",
    limits: "Limits",
    confidence: "Confidence",
    confidencePrefix: "Confidence",
    malformedTitle: "Report section structure error",
    malformedBody: "The backend did not return a complete P16 business_answer. Regenerate the report.",
    chartsAndEvidence: "Charts And Evidence",
    chartAlt: "Report chart",
    unit: "Unit",
    downloadChart: "Download chart",
    chartGenerated: "chart generated",
  },
} as const;

const SECTION_STATUS_LABELS: Record<"zh" | "en", Record<string, string>> = {
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

function TextList({ title, items, emptyText }: { title: string; items?: string[]; emptyText?: string }) {
  const visibleItems = items?.filter((item) => item.trim()) ?? [];
  return (
    <section>
      <h4>{title}</h4>
      {visibleItems.length ? (
        <ul>
          {visibleItems.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : emptyText ? (
        <p>{emptyText}</p>
      ) : null}
    </section>
  );
}

function statusLabel(status: string, language: "zh" | "en") {
  return SECTION_STATUS_LABELS[language][status] ?? status;
}

function businessArtifacts(section: WorkspaceReportSection): ReportBusinessArtifact[] {
  if (section.business_artifacts?.length) {
    return section.business_artifacts;
  }
  return (section.artifact_paths ?? []).map((path) => ({
    type: "chart",
    title: section.title,
    path,
  }));
}

function normalizedArtifactPath(path = "", workspaceId: string, reportId: string) {
  const trimmed = path.trim();
  if (!trimmed) {
    return "";
  }
  if (/^https?:\/\//.test(trimmed) || trimmed.startsWith("/api/")) {
    return trimmed;
  }
  const workspacePrefix = `workspaces/${workspaceId}/`;
  if (trimmed.startsWith(workspacePrefix)) {
    return trimmed.slice(workspacePrefix.length);
  }
  if (trimmed.startsWith("reports/")) {
    return trimmed;
  }
  return `reports/${reportId}/${trimmed}`;
}

function artifactUrl(artifact: ReportBusinessArtifact, workspaceId: string, reportId: string) {
  if (artifact.url?.trim()) {
    return resolveApiUrl(artifact.url);
  }
  const path = normalizedArtifactPath(artifact.path, workspaceId, reportId);
  if (!path) {
    return "";
  }
  if (/^https?:\/\//.test(path) || path.startsWith("/api/")) {
    return resolveApiUrl(path);
  }
  return getWorkspaceArtifactUrl(workspaceId, path);
}

export default function ReportSection({ section, workspaceId, reportId, language = "zh" }: ReportSectionProps) {
  const answer = isBusinessAnswer(section.business_answer) ? section.business_answer : null;
  const artifacts = answer ? businessArtifacts(section) : [];
  const labels = SECTION_LABELS[language];
  const separator = language === "zh" ? "：" : ": ";

  return (
    <ProductCard className="report-section-card">
      <header>
        <h3>{section.title}</h3>
        <StatusPill
          tone={section.status === "completed" ? "green" : section.status === "running" ? "blue" : "orange"}
        >
          {labels.sectionStatus}
          {separator}
          {statusLabel(section.status, language)}
        </StatusPill>
      </header>
      {answer ? (
        <div className="report-business-answer">
          <section>
            <h4>{labels.conclusion}</h4>
            <p className="answer-headline">{answer.headline}</p>
          </section>
          <section>
            <h4>{labels.directAnswer}</h4>
            <p className="answer-summary">{answer.direct_answer}</p>
          </section>
          <section>
            <h4>{labels.why}</h4>
            <p>{answer.why}</p>
          </section>
          <TextList title={labels.keyEvidence} items={answer.evidence_bullets} />
          <TextList title={labels.recommendedActions} items={answer.recommendations} />
          <TextList title={labels.limits} items={answer.caveats} />
          <section>
            <h4>{labels.confidence}</h4>
            <p>{labels.confidencePrefix} {answer.confidence}</p>
          </section>
        </div>
      ) : (
        <section role="alert">
          <h4>{labels.malformedTitle}</h4>
          <p>{labels.malformedBody}</p>
        </section>
      )}
      {artifacts.length ? (
        <section>
          <h4>{labels.chartsAndEvidence}</h4>
          <div className="chart-list">
            {artifacts.map((artifact, index) => {
              const url = artifactUrl(artifact, workspaceId, reportId);
              return (
                <figure key={`${artifact.url || artifact.path || artifact.title}-${index}`} className="chart-artifact">
                  {url ? <img src={url} alt={artifact.title || section.title || labels.chartAlt} /> : null}
                  <figcaption>
                    <strong>{artifact.title || section.title || labels.chartAlt}</strong>
                    {artifact.unit ? <span>{labels.unit}{separator}{artifact.unit}</span> : null}
                    {artifact.business_annotation ? <span>{artifact.business_annotation}</span> : null}
                    {url ? (
                      <a href={url} download>
                        {labels.downloadChart}
                      </a>
                    ) : (
                      <p>{artifact.title || section.title || labels.chartAlt} {labels.chartGenerated}</p>
                    )}
                  </figcaption>
                </figure>
              );
            })}
          </div>
        </section>
      ) : null}
    </ProductCard>
  );
}
