import React from "react";
import type { WorkspaceReportSection } from "../lib/api";

type ReportSectionProps = {
  section: WorkspaceReportSection;
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

export default function ReportSection({ section }: ReportSectionProps) {
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
      {section.artifact_paths?.length ? (
        <section>
          <h4>图表</h4>
          <ul>
            {section.artifact_paths.map((path) => (
              <li key={path}>{path}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </article>
  );
}
