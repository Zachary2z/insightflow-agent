import React from "react";
import type { WorkspaceReportSection } from "../lib/api";

type ReportSectionProps = {
  section: WorkspaceReportSection;
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

export default function ReportSection({ section }: ReportSectionProps) {
  const artifacts = businessArtifacts(section);

  return (
    <article className="panel stack">
      <header>
        <h3>{section.title}</h3>
        <p>章节状态：{statusLabel(section.status)}</p>
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
          <h4>图表</h4>
          <div className="chart-list">
            {artifacts.map((artifact, index) => (
              <figure key={`${artifact.url || artifact.path || artifact.title}-${index}`} className="chart-artifact">
                {artifact.url ? <img src={artifact.url} alt={artifact.title || section.title || "报告图表"} /> : null}
                <figcaption>
                  <strong>{artifact.title || section.title || "报告图表"}</strong>
                  {artifact.url ? null : <p>{artifact.title || section.title || "报告图表"} 图表已生成</p>}
                  {artifact.business_annotation ? <span>{artifact.business_annotation}</span> : null}
                </figcaption>
              </figure>
            ))}
          </div>
        </section>
      ) : null}
    </article>
  );
}
