import React from "react";
import { getWorkspaceArtifactUrl, resolveApiUrl, type WorkspaceReportSection } from "../lib/api";
import ProductCard from "./ProductCard";
import { StatusPill } from "./ProductStatus";

type ReportSectionProps = {
  section: WorkspaceReportSection;
  workspaceId: string;
  reportId: string;
};

type ReportBusinessArtifact = NonNullable<WorkspaceReportSection["business_artifacts"]>[number];

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

export default function ReportSection({ section, workspaceId, reportId }: ReportSectionProps) {
  const artifacts = businessArtifacts(section);

  return (
    <ProductCard className="report-section-card">
      <header>
        <h3>{section.title}</h3>
        <StatusPill
          tone={section.status === "completed" ? "green" : section.status === "running" ? "blue" : "orange"}
        >
          章节状态：{statusLabel(section.status)}
        </StatusPill>
      </header>
      {section.summary ? (
        <section>
          <h4>业务摘要</h4>
          <p>{section.summary}</p>
        </section>
      ) : null}
      {section.error ? (
        <section>
          <h4>状态说明</h4>
          <p role="alert">{section.error}</p>
        </section>
      ) : null}
      {section.evidence_notes?.length ? (
        <section>
          <h4>证据说明</h4>
          <ul>
            {section.evidence_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {artifacts.length ? (
        <section>
          <h4>图表或附件</h4>
          <div className="chart-list">
            {artifacts.map((artifact, index) => {
              const url = artifactUrl(artifact, workspaceId, reportId);
              return (
                <figure key={`${artifact.url || artifact.path || artifact.title}-${index}`} className="chart-artifact">
                  {url ? <img src={url} alt={artifact.title || section.title || "报告图表"} /> : null}
                  <figcaption>
                    <strong>{artifact.title || section.title || "报告图表"}</strong>
                    {artifact.business_annotation ? <span>{artifact.business_annotation}</span> : null}
                    {url ? (
                      <a href={url} download>
                        下载图表
                      </a>
                    ) : (
                      <p>{artifact.title || section.title || "报告图表"} 图表已生成</p>
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
